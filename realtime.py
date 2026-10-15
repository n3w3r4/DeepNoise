"""Keep Windows from throttling the audio process.

The DeepFilterNet plugin runs the model on its own worker thread, and its run() blocks the
audio callback until that thread delivers. Windows 11 throttles processes without a foreground
window (the UI is an Edge window in another process): EcoQoS lowers CPU speed and timer
requests are ignored, so after a quiet stretch the worker wakes late, the plugin underruns and
USB headsets audibly repeat the last buffer. Pro-audio apps avoid this with MMCSS/high priority
(AvSetMmThreadCharacteristics); we do the process-wide equivalent.
"""

import ctypes as C
import sys

_done = False

PROCESS_POWER_THROTTLING_CURRENT_VERSION = 1
PROCESS_POWER_THROTTLING_EXECUTION_SPEED = 0x1
PROCESS_POWER_THROTTLING_IGNORE_TIMER_RESOLUTION = 0x4
ProcessPowerThrottling = 4
HIGH_PRIORITY_CLASS = 0x80


class PROCESS_POWER_THROTTLING_STATE(C.Structure):
    _fields_ = [("Version", C.c_ulong), ("ControlMask", C.c_ulong), ("StateMask", C.c_ulong)]


def boost():
    """Idempotent. Returns a list of what was applied (for logging)."""
    global _done
    if _done or sys.platform != "win32":
        return []
    _done = True
    applied = []
    k32 = C.windll.kernel32
    # HANDLEs are 64-bit; without explicit types ctypes would truncate them to int.
    k32.GetCurrentProcess.restype = C.c_void_p
    k32.SetProcessInformation.argtypes = [C.c_void_p, C.c_int, C.c_void_p, C.c_ulong]
    k32.SetPriorityClass.argtypes = [C.c_void_p, C.c_ulong]
    proc = k32.GetCurrentProcess()

    # Opt out of EcoQoS and of "ignore timer resolution" throttling (StateMask 0 = not throttled).
    st = PROCESS_POWER_THROTTLING_STATE(
        PROCESS_POWER_THROTTLING_CURRENT_VERSION,
        PROCESS_POWER_THROTTLING_EXECUTION_SPEED | PROCESS_POWER_THROTTLING_IGNORE_TIMER_RESOLUTION,
        0,
    )
    if k32.SetProcessInformation(proc, ProcessPowerThrottling, C.byref(st), C.sizeof(st)):
        applied.append("power-throttling off")

    # 1 ms timer so the plugin's 2 ms sleeps are not rounded up to ~15.6 ms.
    if C.windll.winmm.timeBeginPeriod(1) == 0:
        applied.append("timer 1 ms")

    if k32.SetPriorityClass(proc, HIGH_PRIORITY_CLASS):
        applied.append("high priority")
    return applied

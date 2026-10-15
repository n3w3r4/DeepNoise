"""Windows Core Audio helpers (via pycaw/comtypes). Call only from the audio thread (MTA): COM
objects must be created and released on the same thread. Use QueryInterface, never ctypes.cast,
to change interfaces — cast skips AddRef, so both wrappers Release the same pointer and crash.

Covers: device list changes, endpoint volume (read / lock against other apps changing it),
which apps have a stream open on a device, and a global mute hotkey.
"""

import ctypes as C
import os
import warnings
from ctypes import wintypes

try:
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume, IAudioSessionControl2, IAudioSessionManager2
except ImportError:  # optional dependency
    AudioUtilities = None

# pycaw warns for every endpoint property it can't read (e.g. disabled devices); harmless noise.
warnings.filterwarnings("ignore", category=UserWarning, module="pycaw")

_OWN_PID = os.getpid()


def active_endpoints():
    """Frozen set of (name, flow) for active endpoints; flow is 'render' or 'capture'."""
    if AudioUtilities is None:
        return frozenset()
    out = set()
    for d in AudioUtilities.GetAllDevices():
        try:
            if d.FriendlyName and str(d.state).endswith("Active"):
                out.add((d.FriendlyName, "capture" if d.id.startswith("{0.0.1") else "render"))
        except Exception:
            continue
    return frozenset(out)


def _device(name):
    for d in AudioUtilities.GetAllDevices():
        if d.FriendlyName == name and str(d.state).endswith("Active"):
            return AudioUtilities.GetDeviceEnumerator().GetDevice(d.id)
    return None


def process_name(pid):
    k32 = C.windll.kernel32
    k32.OpenProcess.restype = wintypes.HANDLE
    h = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return None
    try:
        buf = C.create_unicode_buffer(512)
        size = wintypes.DWORD(len(buf))
        if k32.QueryFullProcessImageNameW(wintypes.HANDLE(h), 0, buf, C.byref(size)):
            return os.path.splitext(os.path.basename(buf.value))[0]
    finally:
        k32.CloseHandle(wintypes.HANDLE(h))
    return None


def apps_using(name):
    """Names of other processes with an active audio session on endpoint `name`."""
    if AudioUtilities is None or not name:
        return []
    try:
        dev = _device(name)
        if dev is None:
            return []
        mgr = dev.Activate(IAudioSessionManager2._iid_, CLSCTX_ALL, None).QueryInterface(IAudioSessionManager2)
        en = mgr.GetSessionEnumerator()
        apps = set()
        for i in range(en.GetCount()):
            ctl = en.GetSession(i).QueryInterface(IAudioSessionControl2)
            pid = ctl.GetProcessId()
            if ctl.GetState() == 1 and pid not in (0, _OWN_PID):  # AudioSessionStateActive
                n = process_name(pid)
                if n and n.lower() not in ("python", "pythonw", "audiodg"):
                    apps.add(n)
        return sorted(apps)
    except OSError:
        return []


def cable_capture_side(render_name, capture_names):
    """For a virtual cable's playback side ("CABLE Input (...)"), the capture side apps record from."""
    if not render_name or "input" not in render_name.lower():
        return None
    i = render_name.lower().index("input")
    guess = render_name[:i] + "Output" + render_name[i + 5:]
    return guess if guess in capture_names else None


class EndpointVolume:
    """Get/set the Windows volume of one endpoint, rebinding when the device changes."""

    def __init__(self):
        self.name = None
        self.ep = None

    def _bind(self, name):
        self.name, self.ep = name, None
        if AudioUtilities is None or not name:
            return
        dev = _device(name)
        if dev is not None:
            self.ep = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None).QueryInterface(IAudioEndpointVolume)

    def read(self, name):
        """(percent, dB, muted) or None."""
        try:
            if name != self.name or self.ep is None:
                self._bind(name)
            if self.ep is None:
                return None
            return (round(self.ep.GetMasterVolumeLevelScalar() * 100), round(self.ep.GetMasterVolumeLevel(), 1),
                    bool(self.ep.GetMute()))
        except OSError:
            self.name = None
            return None

    def lock(self, name, percent):
        """Enforce `percent` (0-100) and unmute; returns True if it had to correct something."""
        cur = self.read(name)
        if cur is None:
            return False
        changed = False
        if abs(cur[0] - percent) >= 1:
            self.ep.SetMasterVolumeLevelScalar(percent / 100, None)
            changed = True
        if cur[2]:
            self.ep.SetMute(0, None)
            changed = True
        return changed


class Hotkey:
    """Global hotkey (default Ctrl+Alt+M) on its own message-loop thread; calls `callback`."""

    MOD_ALT, MOD_CONTROL, MOD_NOREPEAT = 0x1, 0x2, 0x4000
    WM_HOTKEY = 0x0312

    def __init__(self, callback, vk=0x4D, mods=MOD_CONTROL | MOD_ALT):
        import threading

        self.ok = None
        self._ready = threading.Event()

        def loop():
            u32 = C.windll.user32
            self.ok = bool(u32.RegisterHotKey(None, 1, mods | self.MOD_NOREPEAT, vk))
            self._ready.set()
            if not self.ok:
                return
            msg = wintypes.MSG()
            while u32.GetMessageW(C.byref(msg), None, 0, 0) > 0:
                if msg.message == self.WM_HOTKEY:
                    callback()

        threading.Thread(target=loop, daemon=True, name="hotkey").start()
        self._ready.wait(2)

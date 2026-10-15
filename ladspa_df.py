"""Minimal ctypes host for the official DeepFilterNet LADSPA plugin (deep_filter_ladspa.dll).

Only what the prototype needs: load the DLL, pick a descriptor, instantiate at 48 kHz,
connect audio/control ports and run blocks of float32 samples.
"""

import ctypes as C
from pathlib import Path

import numpy as np

DLL_PATH = Path(__file__).parent / "vendor" / "deep_filter_ladspa.dll"
SAMPLE_RATE = 48_000  # DeepFilterNet3 only runs at 48 kHz

# LADSPA port descriptor bits
PORT_INPUT, PORT_OUTPUT, PORT_CONTROL, PORT_AUDIO = 0x1, 0x2, 0x4, 0x8

LADSPA_Handle = C.c_void_p
LADSPA_Data = C.c_float


class PortRangeHint(C.Structure):
    _fields_ = [("HintDescriptor", C.c_int), ("LowerBound", C.c_float), ("UpperBound", C.c_float)]


class Descriptor(C.Structure):
    pass


# `unsigned long` is 32-bit on Windows x64, which is what c_ulong gives us here.
Descriptor._fields_ = [
    ("UniqueID", C.c_ulong),
    ("Label", C.c_char_p),
    ("Properties", C.c_int),
    ("Name", C.c_char_p),
    ("Maker", C.c_char_p),
    ("Copyright", C.c_char_p),
    ("PortCount", C.c_ulong),
    ("PortDescriptors", C.POINTER(C.c_int)),
    ("PortNames", C.POINTER(C.c_char_p)),
    ("PortRangeHints", C.POINTER(PortRangeHint)),
    ("ImplementationData", C.c_void_p),
    ("instantiate", C.CFUNCTYPE(LADSPA_Handle, C.POINTER(Descriptor), C.c_ulong)),
    ("connect_port", C.CFUNCTYPE(None, LADSPA_Handle, C.c_ulong, C.POINTER(LADSPA_Data))),
    ("activate", C.CFUNCTYPE(None, LADSPA_Handle)),
    ("run", C.CFUNCTYPE(None, LADSPA_Handle, C.c_ulong)),
    ("run_adding", C.CFUNCTYPE(None, LADSPA_Handle, C.c_ulong)),
    ("set_run_adding_gain", C.CFUNCTYPE(None, LADSPA_Handle, LADSPA_Data)),
    ("deactivate", C.CFUNCTYPE(None, LADSPA_Handle)),
    ("cleanup", C.CFUNCTYPE(None, LADSPA_Handle)),
]

_dll = None


def _load():
    global _dll
    if _dll is None:
        _dll = C.CDLL(str(DLL_PATH))
        _dll.ladspa_descriptor.restype = C.POINTER(Descriptor)
        _dll.ladspa_descriptor.argtypes = [C.c_ulong]
    return _dll


def descriptors():
    """Yield every descriptor the plugin library exposes."""
    dll = _load()
    i = 0
    while True:
        d = dll.ladspa_descriptor(i)
        if not d:
            return
        yield d.contents
        i += 1


def ports(desc):
    """Return [(index, name, flags, (lower, upper))] for a descriptor."""
    out = []
    for i in range(desc.PortCount):
        hint = desc.PortRangeHints[i]
        out.append((i, desc.PortNames[i].decode(), desc.PortDescriptors[i], (hint.LowerBound, hint.UpperBound)))
    return out


# Upstream defaults of the DeepFilterNet LADSPA plugin (ladspa/src/lib.rs, v0.5.6).
# The port range lower bounds are NOT sane defaults: max thresholds at -15 dB disable processing.
DEFAULT_CONTROLS = {
    "Attenuation Limit": 100.0,
    "Min processing threshold": -15.0,
    "Max ERB processing threshold": 35.0,
    "Max DF processing threshold": 35.0,
    "Min Processing Buffer": 0.0,
    "Post Filter Beta": 0.0,
}


class DeepFilterMono:
    """One mono DeepFilterNet3 instance. Feed it float32 blocks with process()."""

    def __init__(self, max_block=4096, controls=None):
        controls = {**DEFAULT_CONTROLS, **(controls or {})}
        self.desc = next(d for d in descriptors() if b"mono" in d.Label.lower())
        self._keep = self.desc  # keep the struct alive while the handle is in use
        self.handle = self.desc.instantiate(C.byref(self.desc), SAMPLE_RATE)
        if not self.handle:
            raise RuntimeError("DeepFilterNet LADSPA instantiate failed")
        self.max_block = max_block
        self.inp = np.zeros(max_block, np.float32)
        self.out = np.zeros(max_block, np.float32)
        self.controls = {}
        audio_in = audio_out = None
        for i, name, flags, (lo, hi) in ports(self.desc):
            if flags & PORT_AUDIO:
                if flags & PORT_INPUT:
                    audio_in = i
                else:
                    audio_out = i
            elif flags & PORT_CONTROL:
                cell = (C.c_float * 1)(lo)
                self.controls[name] = cell
                self.desc.connect_port(self.handle, i, C.cast(cell, C.POINTER(LADSPA_Data)))
        self._fp = C.POINTER(LADSPA_Data)
        self.desc.connect_port(self.handle, audio_in, self.inp.ctypes.data_as(self._fp))
        self.desc.connect_port(self.handle, audio_out, self.out.ctypes.data_as(self._fp))
        for name, value in controls.items():
            self.set_control(name, value)
        if self.desc.activate:
            self.desc.activate(self.handle)

    def set_control(self, name_part, value):
        """Set the first control port whose name contains name_part (case-insensitive)."""
        for name, cell in self.controls.items():
            if name_part.lower() in name.lower():
                cell[0] = float(value)
                return name
        raise KeyError(f"no control port matching {name_part!r}: {list(self.controls)}")

    def process(self, block):
        n = len(block)
        if n > self.max_block:
            raise ValueError("block larger than max_block")
        self.inp[:n] = block
        self.desc.run(self.handle, n)
        return self.out[:n].copy()

    def close(self):
        if self.handle:
            if self.desc.deactivate:
                self.desc.deactivate(self.handle)
            self.desc.cleanup(self.handle)
            self.handle = None


if __name__ == "__main__":
    for d in descriptors():
        print(f"[{d.UniqueID}] {d.Label.decode()} — {d.Name.decode()} ({d.Maker.decode()})")
        for i, name, flags, rng in ports(d):
            kind = ("audio" if flags & PORT_AUDIO else "control") + (" in" if flags & PORT_INPUT else " out")
            print(f"   {i}: {kind:12} {name}  range={rng}")

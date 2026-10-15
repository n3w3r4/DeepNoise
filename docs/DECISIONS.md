# Implementation decisions

Newest first. Each entry records what was decided and why, so a later change doesn't undo it by accident.

## 2026-10-15: Core Audio objects live and die on the audio thread

All pycaw/comtypes objects are created and released on the audio thread (COM MTA), and interface changes use
`QueryInterface`. Two crashes led here: the device list was first created on the GUI thread and garbage-collected
on the audio thread (an apartment mismatch), and `ctypes.cast` between interfaces skipped `AddRef`, so two
wrappers released one pointer. Both showed up only at random garbage collections, so `faulthandler` now writes
every native crash's Python stack to the log. The audio loop also runs `gc.collect()` after each device scan, so
COM wrappers are freed on the thread that created them.

## 2026-10-15: Native WebView2 windows instead of Edge app windows

The first tray flyout was an Edge `--app` window restyled with Win32. Edge draws its own title bar inside the
window, so removing the caption needed a clipping region sized from the page's `outerHeight - innerHeight`, which
left a band and frame on some setups. pywebview hosts WebView2 in a real frameless window instead, and gives the
main window a native frame with the app icon. pywebview needs the main thread, so the engine moved to its own
audio thread (see the decision above).

## 2026-10-15: The flyout hides on focus loss only after it had focus once

`SetForegroundWindow` only works for the process that received the last input. When the flyout was opened by
something other than a click on our tray icon, it never got focus and the auto-hide closed it at once. The
flyout now attaches to the foreground thread's input queue to take focus, and auto-hide waits until it has had
focus at least once.

## 2026-10-15: Process-wide real-time settings

Without a foreground window, Windows 11 applies EcoQoS and ignores timer-resolution requests for the process.
The DeepFilterNet plugin sleeps in 2 ms steps waiting for its worker, so those sleeps became ~15.6 ms and
caused underruns. `realtime.boost()` opts out of power throttling, requests a 1 ms timer and raises the process
priority.

## 2026-10-15: Pause gate with hold

A plain gate closes between words and reopens on the next syllable, so the residual noise pumps in and out.
The gate stays open 250 ms after the last loud block, then closes over 150 ms to −40 dB.

## 2026-10-14: DeepFilterNet through its official LADSPA plugin

The published DeepFilterNet3 ONNX graphs process whole sequences and expose no recurrent state, so they can't
stream 10 ms frames. The official v0.5.6 LADSPA plugin embeds the model and streams; DeepNoise hosts it through
`ctypes` and verifies the downloaded DLL by size and SHA-256. The plugin expects real-time pacing: feeding it
faster than real time produces underruns, which is why `tools/bench_file.py` sleeps between blocks.

## 2026-10-14: Suppression level as a dry/wet blend

The "Strength" control blends the original and the filtered signal (`out = (1 − a)·dry + a·wet`). The dry path
is delayed by the plugin's measured 40 ms latency so the two stay aligned.

## 2026-10-14: VB-Audio cables are installed by the user, not bundled

VB-CABLE may be redistributed with attribution, but Hi-Fi Cable has no stated redistribution terms and both are
kernel drivers that need elevation. `scripts/install-drivers.ps1` downloads them from VB-Audio, checks their
Authenticode signature and runs their installers; DeepNoise never ships them.

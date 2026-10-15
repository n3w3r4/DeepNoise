# Repository guidance

Read README.md, CONTRIBUTING.md, and SECURITY.md before changing behavior.
Use English for code and documentation; preserve the pt-BR translation and guide.
Keep engine status codes synchronized with both HTML interfaces.
Run Ruff, Python unit tests, and the Node UI checks for relevant changes.
Do not start audio capture, install drivers, or stop a running app for automated tests.
Keep logs, recordings, user settings, binaries, and unrelated analysis out of Git.
Preserve copyright notices and record new asset provenance in ATTRIBUTION.md.

---

# Guide for AI agents and contributors

DeepNoise is a Windows tray app for real-time AI noise cancellation: a Python audio engine
(PortAudio/WASAPI, the native DeepFilterNet3 LADSPA plugin, WebRTC AEC3) with an HTML interface
rendered in native WebView2 windows. The product name is always written **DeepNoise** in
user-facing text; machine names stay lowercase (`deepnoise.log`, `deepnoise-source.png`).

## 1. Orientation (5 minutes)

| Read | Why |
|---|---|
| `README.md` | What it does, install, build, project layout |
| `docs/ARCHITECTURE.md` | Threads, audio graph, the UI ↔ engine seam |
| `docs/DEVELOPMENT.md` | Set up, run, test, debug, diagnostics tools |
| `docs/DECISIONS.md` | Why things are the way they are (read before "simplifying" something) |
| `CONTRIBUTING.md` | Language, tests, commits, licensing of contributions |
| `SECURITY.md` | Loopback API trust boundary, diagnostics privacy |
| `docs/LICENSE_AUDIT.md`, `THIRD_PARTY_NOTICES.md` | Third-party licensing state, including open items |
| `ROADMAP.md`, `CHANGELOG.md` | Stage, what's next, what changed |

## 2. Code map

```text
app.py          app state, loopback HTTP server, audio thread loop, tray + windows wiring, single instance
local_api.py    request checks for the loopback API (Host/Origin/Sec-Fetch-Site, POST header, bounded JSON)
engine.py       AudioEngine: mic chain, speaker chain, monitor, watchdog, device resolution, diagnostics ring
ladspa_df.py    ctypes host for vendor/deep_filter_ladspa.dll (DeepFilterNet3)
mixer.py        DryWetMixer, NoiseGate (with hold), HighPass
winaudio.py     Windows Core Audio via pycaw/comtypes: endpoints, volume lock, sessions, global hotkey
windows.py      pywebview windows: main window (X hides) and the frameless tray flyout
desktop.py      tray icon (pystray), app/tray icon rendering, start with Windows (HKCU Run)
realtime.py     opts the process out of Windows power throttling, 1 ms timer, high priority
ui/             index.html (main), flyout.html (quick actions), i18n.js (en-US / pt-BR), api.js, style.css
tools/          bench_file.py, check_mic.py, analyze_diag.py (manual tools; they open audio devices)
scripts/        fetch_deps.py, install-drivers.ps1, license/source collection, release verification
tests/          Python unit/HTTP/packaging tests and tests/test_ui.cjs (Node) — no audio devices
```

## 3. Invariants (each one was learned from a real bug)

- **One thread owns the hardware.** PortAudio streams and every Core Audio (COM) object are created *and
  released* on the audio thread, initialized as MTA (`comtypes.CoInitializeEx(COINIT_MULTITHREADED)`). HTTP,
  tray and GUI threads hand device work to it with `App.run_main()` (executed by `App.pump()` in the audio
  loop). Opening WASAPI streams from
  another thread fails, and a COM object freed by the garbage collector on another thread crashes the process.
- **Change COM interfaces with `QueryInterface`, never `ctypes.cast`.** `cast` skips `AddRef`, so two wrappers
  release the same pointer and the process dies later, at a random garbage collection.
- **pywebview owns the main thread** (`webview.start()`); window calls from other threads are marshalled for you.
- **Never block or allocate heavily in audio callbacks.** The DeepFilterNet plugin's `run()` waits for its worker
  thread; anything slower than the 10 ms block budget becomes audible dropouts. Log from the audio loop, not callbacks.
- **Status codes are language-independent**: `stopped`, `running`, `waiting`, `error`. The engine, `app.py`,
  `desktop.py`, `ui/index.html` and `ui/flyout.html` must agree; `tests/test_ui.cjs` checks the HTML side.
- **Translations stay in parity**: every key exists in both `en-US` and `pt-BR` in `ui/i18n.js` (checked by
  `tests/test_ui.cjs`); tray menu text lives in `desktop.TRAY_TEXT`. UI text never names third-party internals.
- **The loopback API is not public**: every request goes through `local_api.allowed_request`; UI requests use
  `ui/api.js` (`localFetch`) so the custom header is always sent.
- **Devices are referenced by name**, not PortAudio index: indexes change whenever PortAudio is re-initialized.

## 4. Before you finish

```powershell
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m unittest discover -s tests -v
node tests/test_ui.cjs
```

UI changes: verify visually (see `docs/DEVELOPMENT.md` › Screenshots without audio) in both languages and both
Windows themes. Audio changes: describe the manual test you ran (devices, what you heard, the log) in the PR;
automated checks never open audio devices.

# Development

Windows 10/11 x64, Python 3.14, and Node.js 22+ (only for the UI checks).

## Set up

```powershell
py -3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install --require-hashes -r requirements-lock.txt
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe scripts\fetch_deps.py      # vendor\deep_filter_ladspa.dll, SHA-256 checked
```

## Run

```powershell
run-dev.cmd                                          # tray + main window, from source
.venv\Scripts\python.exe app.py --tray               # start in the tray only (what "Start with Windows" does)
.venv\Scripts\python.exe app.py --no-window --console --port 8766 --config test-settings.json
```

`--no-window` runs the engine and the loopback API without tray or windows (the audio loop then runs on the
main thread); `--console` keeps the log on the terminal; `--config` points at a different settings file, so
you can test with silent devices without touching your own settings. Only one windowed instance runs per
user: a second launch asks the first one to show its window and exits.

From source, `settings.json`, `instance.json`, `logs\` and `webview\` live in the repository folder and are
git-ignored. The packaged `.exe` uses `%APPDATA%\DeepNoise`.

## Test

```powershell
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m unittest discover -s tests -v
node tests/test_ui.cjs
```

None of these open audio devices. `tests/test_ui.cjs` checks the HTML/JS syntax, that both pages use the
engine's status codes, that `en-US` and `pt-BR` have the same keys, and that requests go through `ui/api.js`.

## Debug

- **Log**: `logs\deepnoise.log` (packaged: `%APPDATA%\DeepNoise\logs\`). It records startup, device changes,
  watchdog restarts, buffer dropouts, a 30 s trend line (mic volume, noise floor, output level) and the
  DeepFilterNet plugin's own warnings (stderr is redirected there).
- **Native crashes** (access violations in COM, ctypes or the plugin) are written by `faulthandler` with every
  thread's Python stack. Look for `Windows fatal exception` and the `Current thread` block.
- **Save diagnostics** (main window footer, or `POST /api/diag`) writes the last 60 s of three signals:
  `diag-*-1-mic.wav` (after high-pass/AEC), `diag-*-2-deepfilternet.wav`, `diag-*-3-output.wav`.
  These files contain real audio; don't attach them to public issues.

## Tools

These open audio devices; run them by hand, never from automated tests.

| Tool | What |
|---|---|
| `tools/analyze_diag.py logs/diag-YYYYmmdd-HHMMSS` | Per-second levels, mic→filter delay drift, repeated segments |
| `tools/bench_file.py in.wav [out.wav]` | Runs a 48 kHz mono WAV through DeepFilterNet at real-time pace: latency, block timing, noise-floor reduction |
| `tools/check_mic.py -i "Mic name"` | Records N seconds from a mic through DeepFilterNet without playing anything back |
| `tools/ui_demo_server.py` | The UI with a fake engine (no audio), for UI work and screenshots |

## Screenshots without audio

```powershell
.venv\Scripts\python.exe tools\ui_demo_server.py --port 8790
& "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe" --headless=new --hide-scrollbars `
  --force-device-scale-factor=2 --blink-settings=preferredColorScheme=0 --virtual-time-budget=4500 `
  --window-size=936,1400 --screenshot=overview-raw.png http://127.0.0.1:8790/_showcase.html
```

Headless Edge removes about 200 px from the window height and enforces a ~500 px minimum width, so capture
`/_showcase.html` (both screens at their real sizes inside a wider page) with a taller window, then crop to
1872 × 2200. Restart the demo server between captures: each page gets one meter stream per server run.
Record new images in `ATTRIBUTION.md`.

## Build

```powershell
.venv\Scripts\python.exe build.py
```

See [`RELEASING.md`](RELEASING.md) for what the build produces and how releases are verified and published.

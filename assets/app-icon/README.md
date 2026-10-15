# DeepNoise app icon

| File | What |
|---|---|
| `deepnoise-source.png` | Master artwork, 1254 × 1254 px: engraving-style headphones on a blue field |
| `../../ui/icon.png` | 256 px rounded icon used by the windows, the web UI and as the tray-icon base |
| `build/DeepNoise.ico` (generated) | Windows icon embedded in `DeepNoise.exe`: 16, 20, 24, 32, 40, 48, 64, 128 and 256 px |

The derived files are produced by `desktop.app_icon()` and `desktop.save_ico()`; `build.py`
regenerates both on every build. Small sizes (48 px and below) get a light unsharp mask so the
engraving lines stay readable, and every size has Windows 11-style rounded corners.

The tray icon adds DeepNoise's status on top of the artwork at runtime (`desktop.make_icon_image`):
red LED = live, amber LED = waiting for a device, greyed = unfiltered, greyed with a red slash = muted.

Provenance and license: see [`LICENSE.txt`](LICENSE.txt) and [`ATTRIBUTION.md`](../../ATTRIBUTION.md).

# Third-party notices

DeepNoise is built on the projects below. The release `.exe` bundles the runtime components listed
in the first table; release builds collect available installed license files into `licenses/` and record versions in
`DEPENDENCIES.json`. This inventory also includes build-environment tools. See [the native review](docs/LICENSE_AUDIT.md)
for scope, source provenance, and the unresolved LiveKit redistribution item.

| Component | Use in DeepNoise | License |
|---|---|---|
| [DeepFilterNet](https://github.com/Rikorose/DeepFilterNet) v0.5.6 (LADSPA plugin + DeepFilterNet3 model) | Neural noise suppression | MIT or Apache-2.0 |
| [LiveKit Python SDK](https://github.com/livekit/python-sdks) (WebRTC audio processing) | Echo cancellation (AEC3) | Apache-2.0 plus WebRTC and bundled third-party terms, including LGPL libsoxr; see native review |
| [sounddevice](https://github.com/spatialaudio/python-sounddevice) + [PortAudio](https://www.portaudio.com) | Audio I/O (WASAPI) | MIT |
| [NumPy](https://numpy.org) | Signal buffers | BSD-3-Clause |
| [SciPy](https://scipy.org) | High-pass filter | BSD-3-Clause |
| [pycaw](https://github.com/AndreMiras/pycaw) + [comtypes](https://github.com/enthought/comtypes) | Windows Core Audio (volume, sessions) | MIT |
| [pywebview](https://pywebview.flowrl.com) + [pythonnet](https://github.com/pythonnet/pythonnet) | Native windows (Edge WebView2) | BSD-3-Clause / MIT |
| [pystray](https://github.com/moses-palmer/pystray) | System tray icon | LGPL-3.0 |
| [Pillow](https://python-pillow.org) | Tray/app icons | MIT-CMU (HPND) |
| [PyInstaller](https://pyinstaller.org) bootloader | `DeepNoise.exe` | GPL-2.0 with bootloader exception |

## Not bundled

**VB-CABLE** and **VB-Audio Hi-Fi Cable** are made by [VB-Audio Software](https://vb-audio.com) and are
**donationware** (www.vb-cable.com). DeepNoise does not include them; `scripts/install-drivers.ps1`
downloads them from VB-Audio's official server, checks the digital signature and runs their installers.
If you find them useful, please support VB-Audio: https://shop.vb-audio.com

Microsoft Edge **WebView2 Runtime** is used, not redistributed. Install it from Microsoft if missing.
The **WebView2 SDK assemblies and loader** are bundled through pywebview. Their matching
1.0.3856.49 LICENSE and NOTICE are included under `licenses/native/`.
Only the non-ASIO Windows x64 PortAudio DLL is bundled.

## pystray (LGPL-3.0)

The frozen application ships pystray as editable source in `_internal/pystray`.
Its GPL and LGPL license texts are copied to `licenses/pystray`. You may modify or
replace that compatible library and restart DeepNoise; see docs/RELEASING.md.

## Release review

See `docs/LICENSE_AUDIT.md` for the completed inventory review and remaining binary
redistribution work. In particular, LiveKit statically links libsoxr under LGPL-2.1-or-later
and includes FFmpeg-related code through WebRTC. The source/relink requirements are
not satisfied merely by including notice texts. A complete reconstruction package
has not yet been validated. Original project licensing does not override those terms.

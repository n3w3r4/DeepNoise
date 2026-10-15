# Third-party notices

DeepNoise is built on the projects below. The release `.exe` bundles the runtime components listed
in the first table; their license texts are available at the linked projects.

| Component | Use in DeepNoise | License |
|---|---|---|
| [DeepFilterNet](https://github.com/Rikorose/DeepFilterNet) v0.5.6 (LADSPA plugin + DeepFilterNet3 model) | Neural noise suppression | MIT or Apache-2.0 |
| [LiveKit Python SDK](https://github.com/livekit/python-sdks) (WebRTC audio processing) | Echo cancellation (AEC3) | Apache-2.0 (WebRTC: BSD-3-Clause) |
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

Microsoft Edge **WebView2 Runtime** ships with Windows 10/11 and is used, not redistributed.

# Changelog

## 0.1.0 - unreleased

- Initial Windows desktop application with microphone and incoming-audio suppression.
- English and Brazilian Portuguese UI, tray, audio routing, and diagnostics.
- English internal status codes synchronized across the engine and both UI windows.
- Loopback request origin checks and bounded JSON parsing.
- MIT OR Apache-2.0 licensing for original code, third-party notices, contribution
  guidance, automated checks, and draft release packaging.

- Expanded native dependency notices and actual DLL/PYD hash inventory; included
  pystray and LiveKit Rust source snapshots and documented the remaining static
  LGPL/FFmpeg reconstruction issue.
- Excluded unused ASIO and non-x64 PortAudio DLLs from Windows packages.
- Locked build dependencies by hash and added source archives, release verification,
  and a draft-only GitHub publication flow for n3w3r4/DeepNoise.
- Documentation organized like PhotoCraft: app icon under `assets/app-icon/` with its own
  README and license, attribution table by path, development guide, decision log, an expanded
  `AGENTS.md`, and a demo-data overview screenshot in the README.

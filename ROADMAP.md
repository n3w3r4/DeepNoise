# Roadmap

## Available in 0.1.0

- Microphone and incoming-audio suppression with DeepFilterNet3.
- Optional WebRTC echo cancellation and virtual cable routing.
- Windows tray, quick actions, mute shortcut, and automatic device reconnection.
- English and Brazilian Portuguese interfaces.

## Before the first public release

- Complete the LiveKit LGPL/FFmpeg corresponding-source and relink work in docs/LICENSE_AUDIT.md.
- Validate Windows microphone/speaker routing and reconnect behavior on real hardware.
- Enable private vulnerability reporting on n3w3r4/DeepNoise (remote configured).
- Run CI and review the draft release, source archive, and checksums.

## Future work (not commitments)

- Broader device coverage and repeatable latency/quality measurements.
- More robust settings validation and diagnostic controls.
- Signed Windows builds and a simpler installation experience.

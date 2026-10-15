# DeepNoise 0.1.0 — Windows preview

Real-time local noise suppression for your microphone and incoming call audio,
with DeepFilterNet3, optional WebRTC echo cancellation, tray controls, device
reconnection, and English / Brazilian Portuguese interfaces.

## Download and run

Extract `DeepNoise-0.1.0-win64.zip` and run `DeepNoise.exe`. Windows 10/11 x64 and
WebView2 Runtime are required. Virtual routing uses separately installed VB-Audio
cables. `SHA256SUMS.txt` covers the binary and source archives.

The release is unsigned. This preview has automated checks and packaging validation;
live audio quality, routing and reconnection require hardware testing.

## Licenses and source

Original DeepNoise source: MIT OR Apache-2.0. Third-party components retain their
own terms. Notices, a native inventory, dependency versions and selected upstream
source snapshots are included. ASIO DLLs are not distributed.

**Draft limitation:** the LiveKit FFI includes statically linked libsoxr (LGPL)
and FFmpeg-related WebRTC code. A complete, tested corresponding-source/relink
package for that exact binary has not been established. Keeping these components
does not resolve their redistribution obligations. See `docs/LICENSE_AUDIT.md`.

Do not describe this draft as a completed licensing clearance.

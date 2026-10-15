# Native dependency review — 2026-10-15

Scope: Windows x64 release candidate, CPython 3.14.6, dependencies in
`requirements-lock.txt`. This is an engineering inventory and source review.
It is not a certification that every redistribution requirement is satisfied.

## Result

The source repository and draft release materials are prepared. **A binary
redistribution issue remains open for LiveKit's statically linked dependencies.**
The maintainer requested retaining AEC and continuing preparation with that issue
documented. This decision does not waive upstream license requirements.

## Evidence and actions

| Native component | Evidence / terms | Action |
| --- | --- | --- |
| DeepFilterNet 0.5.6 | Official DLL SHA-256 pinned by `fetch_deps.py`; original code MIT OR Apache-2.0 | MIT text and conservative Cargo.lock dependency notices included |
| LiveKit Python 1.1.20 / FFI 0.12.80 | Python tag `rtc-v1.1.20`, commit `ee527bd258e277149e2144a870aaec817dae24b4`; rust submodule `5a656c4bc4bc5c4f7fad17ab69044db3b487dfeb` | Apache text, NOTICE, wheel's WebRTC notices, Rust dependency notices and source snapshot included |
| libsoxr inside LiveKit | `soxr-sys/src/LICENCE`: LGPL-2.1-or-later; `build.rs` compiles `libsoxr.a` | License added; source snapshot includes vendored libsoxr; complete rebuild/relink path remains unvalidated |
| FFmpeg inside LiveKit WebRTC | Windows build enables H.264 and Chrome FFmpeg branding; license-generation patch copies GPLv2, GPLv3, LGPLv2.1 and LGPLv3 texts together | Keep upstream notices; presence of all four texts alone does not establish which license applies to the actual build |
| PortAudio | sounddevice's Windows binaries include optional ASIO and multiple architectures | Package only `libportaudio64bit.dll` without ASIO; add PortAudio license |
| WebView2 SDK 1.0.3856.49 | Installed DLL version and matching NuGet package LICENSE / NOTICE | Include both texts; distinguish bundled SDK/loader from separately installed runtime |
| NumPy / SciPy | Installed wheel license files include OpenBLAS and other compiled-code notices | Collect complete wheel notices, including files whose names use LICENCE |
| Pillow | Wheel LICENSE includes native dependencies such as FreeType and image codecs | Retain complete file, not only Pillow's introductory license |
| CPython and extension libraries | CPython 3.14.6 LICENSE and Windows build dependency versions | Add OpenSSL, libffi, Expat, xz/liblzma, zlib-ng and zstd notices |
| pystray | LGPL-3.0, pure Python | Keep replaceable source, GPL/LGPL texts and original source snapshot |
| PyInstaller bootloader | GPL with distribution exception in COPYING.txt | Retain full exception text |
| Windows runtime DLLs | Microsoft binaries supplied with Python/wheels | Retain provider notices; these are not relicensed by DeepNoise |

## Source and notice provenance

`licenses/native/provenance.json` records downloaded notice URLs and checksums.
The DeepFilterNet closure contains 292 packages; the LiveKit closure contains 542.
These are conservative Cargo.lock closures, including optional, test, build and
non-Windows dependencies. They are not exact linked-code SBOMs. Registry archives
were compared against Cargo.lock checksums. Local/git dependencies and absent
standalone license files remain identifiable in the JSON inventories.

`NATIVE_DEPENDENCIES.json` in each build records actual bundled DLL/PYD paths,
hashes, and notice groups. Unclassified binaries fail the build. This verifies
inventory coverage, not legal completeness or reproduction of upstream builds.

The original DeepFilterNet release workflow does not establish a reproducible
build attestation for the downloaded DLL. The pinned DLL hash prevents unnoticed
changes; the tag's lockfile supplies a conservative notice baseline.

## Open binary-distribution item

Before representing this build as fully cleared for public redistribution:

1. Identify the exact FFmpeg revision, configuration and patches in WebRTC
   `webrtc-89d790b`, and establish the applicable license for that build.
2. Supply corresponding sources and the materials required to modify/relink
   the statically linked LGPL components, with a tested reconstruction procedure.
3. Validate the complete source offer/archive against the exact distributed DLL.
   The included Rust SDK snapshot is useful evidence, but does not include every
   WebRTC dependency, Git submodule or a validated set of relink objects.

The alternative is to replace the full LiveKit FFI with a reviewed audio-only AEC
implementation. The present change keeps functionality intact.

## Primary references

- [LiveKit's vendored libsoxr license](https://github.com/livekit/rust-sdks/blob/5a656c4bc4bc5c4f7fad17ab69044db3b487dfeb/soxr-sys/src/LICENCE)
- [LiveKit's libsoxr build](https://github.com/livekit/rust-sdks/blob/5a656c4bc4bc5c4f7fad17ab69044db3b487dfeb/soxr-sys/build.rs)
- [WebRTC license collection patch](https://github.com/livekit/rust-sdks/blob/5a656c4bc4bc5c4f7fad17ab69044db3b487dfeb/webrtc-sys/libwebrtc/patches/add_licenses.patch)
- [FFmpeg redistribution guidance](https://ffmpeg.org/legal.html)
- [WebView2 package](https://www.nuget.org/packages/Microsoft.Web.WebView2/1.0.3856.49)
- [sounddevice's optional ASIO support](https://python-sounddevice.readthedocs.io/en/latest/installation.html#asio-support)

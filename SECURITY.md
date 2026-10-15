# Security and privacy

DeepNoise is an early Windows desktop application. Security fixes target the current
development branch; there is no long-term support commitment for older builds.

## Reporting

Use the repository's private GitHub vulnerability reporting feature when enabled.
If unavailable, ask the maintainer for a private reporting channel without including
exploit details, recordings, credentials, or personal information in a public issue.
No dedicated security mailbox has been configured.

## Local boundary

The control server binds to `127.0.0.1` on a random port by default. It validates
Host and Origin and requires a custom header for POST requests. It does not enable
CORS. This blocks ordinary cross-site browser control, but does not authenticate
other local programs or protect against malware running as the same Windows user.
Never expose this server through a network proxy or bind it to a public interface.

Audio processing runs locally. The diagnostic buffer holds recent audio in memory;
clicking Save diagnostics writes up to 60 seconds of microphone, filtered, and output
audio to disk. These files can contain private conversations. Review before sharing.
Settings, logs, and WebView2 storage live in `%APPDATA%\DeepNoise` in packaged builds,
or the repository directory when running from source.

Dependency setup downloads the native plugin with a pinned SHA-256. The optional
driver helper downloads VB-Audio installers and verifies their signatures before
requesting elevation. DeepNoise does not redistribute those drivers.

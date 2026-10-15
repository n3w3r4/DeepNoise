# Contributing

Use English for code, comments, logs, issues, pull requests, and primary documentation.
Preserve Brazilian Portuguese translations in `ui/i18n.js`, `desktop.py`, and
`docs/README.pt-BR.md`. Keep machine-readable status codes language-independent.

## Development

Follow the source setup in README.md (Windows x64, Python 3.14), then install
`requirements-dev.txt`. Run:

```powershell
python -m ruff check .
python -m unittest discover -s tests -v
node tests/test_ui.cjs
python scripts/fetch_deps.py
python build.py
```

Node.js 22 or newer is used only by the UI checks, not by the desktop application.
Tests do not open audio devices. Manually test microphone and speaker routing, mute,
device reconnection, tray actions, and both languages on Windows before a release.

## Changes and Git

Keep commits focused, with imperative English subjects (for example,
`fix: keep UI status in sync with the audio engine`). Explain the problem, result,
and validation in pull requests. Preserve existing history; do not rewrite shared commits.
Never commit user settings, logs, recordings, downloaded binaries, or unrelated analyses.

Add regression coverage for behavior changes. Include license notices for dependencies
and asset provenance in ATTRIBUTION.md. Contributions to original project code are
provided under MIT OR Apache-2.0 unless explicitly agreed otherwise.

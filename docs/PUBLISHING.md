# GitHub publication handoff

Destination: https://github.com/n3w3r4/DeepNoise

The local `origin` points to this repository. No push or public release is performed
by preparing these files. Review `docs/LICENSE_AUDIT.md` before distributing binaries.

From a clean checkout after reviewing the current commit:

```powershell
git push -u origin main
git tag -a v0.1.0 -m "DeepNoise 0.1.0 Windows preview"
git push origin v0.1.0
```

The version tag starts the Windows workflow. It tests, builds and uploads binary
and source archives with checksums, then creates a draft release using the exact
notes in `docs/RELEASE_NOTES.md`. It never publishes that draft automatically.
GitHub Actions must be enabled. Do not move an existing tag to a different commit.

Before publication, review the draft's assets, known licensing limitation and hardware
validation. Enable private vulnerability reporting in the repository settings.
The local commit history is preserved, including its existing author metadata.

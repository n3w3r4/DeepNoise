# Releasing DeepNoise

1. Complete the checks in CONTRIBUTING.md and the hardware smoke test below.
2. Keep artwork provenance in ATTRIBUTION.md current and review license coverage for
   transitive native code in DeepFilterNet and LiveKit/WebRTC. Automatically collected
   Python metadata is a useful inventory, not proof that all native notices are present.
3. Update `version.py` and CHANGELOG.md, commit the reviewed source, and configure
   the intended GitHub remote. Never include the separate Krisp report/prototype.
4. Run `python build.py`. If the installed app is running, use
   `python build.py --dist-dir dist/candidate` to avoid overwriting its files.
5. Inspect the ZIP, `SHA256SUMS.txt`, notices, dependency manifest, and editable
   `_internal/pystray` source. Test extraction into a fresh folder.
6. Push the reviewed source and a matching `v<version>` tag. The release workflow
   builds Windows artifacts and creates a **draft** GitHub release with GitHub CLI.
7. Review the draft and publish manually after resolving all release checks.

## Hardware smoke test

Test both English and pt-BR in the main window and flyout, microphone mute and
Ctrl+Alt+M, cable routing in a call app, incoming-audio filtering, speaker echo,
device unplug/replug, closing to tray, and starting a second instance.
Check logs and test diagnostic saving only with consent from recorded participants.

## pystray and third-party source

The LGPL pystray package is collected as editable Python source rather than embedded
bytecode. Users can replace `_internal/pystray` with a compatible modified version
and restart the app. Its license files accompany the package. Rebuilding the entire
application from the published source is also supported by README.md.
Do not remove these files or prohibit modifications/debugging of this component.
Other third-party components retain their respective terms.

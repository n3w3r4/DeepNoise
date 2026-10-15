"""Download the native DeepFilterNet plugin into vendor/ (not committed: 48 MB binary).

  python scripts/fetch_deps.py

Source: the official DeepFilterNet v0.5.6 GitHub release (MIT/Apache-2.0). The file is checked
against the size published by GitHub and the SHA-256 recorded below before it is accepted.
"""

import hashlib
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEPS = [
    {
        "name": "DeepFilterNet LADSPA plugin (DeepFilterNet3 model embedded)",
        "url": "https://github.com/Rikorose/DeepFilterNet/releases/download/v0.5.6/deep_filter_ladspa-0.5.6-x86_64-pc-windows-msvc.dll",
        "dest": ROOT / "vendor" / "deep_filter_ladspa.dll",
        "size": 50_671_104,
        "sha256": "f97e34275eb884b6076a96d261683d2a43c6b2d97ddf9e346bc06f7c8057eb04",
    },
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(dep):
    dest = dep["dest"]
    if dest.exists() and dest.stat().st_size == dep["size"] and sha256(dest) == dep["sha256"]:
        print(f"ok (already present): {dest.relative_to(ROOT)}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    print(f"downloading {dep['name']}\n  {dep['url']}")
    with urllib.request.urlopen(dep["url"], timeout=60) as r, open(tmp, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    size, digest = tmp.stat().st_size, sha256(tmp)
    if size != dep["size"] or digest != dep["sha256"]:
        tmp.unlink()
        sys.exit(f"ERROR: unexpected file (size {size}, sha256 {digest}); nothing was installed")
    tmp.replace(dest)
    print(f"ok: {dest.relative_to(ROOT)} ({size / 1e6:.1f} MB, sha256 verified)")


if __name__ == "__main__":
    for d in DEPS:
        fetch(d)

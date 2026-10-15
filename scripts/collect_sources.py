"""Copy checksum-pinned upstream source snapshots; not a complete native rebuild kit."""
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def collect(app_dir):
    rows = json.loads((ROOT / "packaging/source-snapshots.json").read_text(encoding="utf-8"))
    dest = app_dir / "sources"
    dest.mkdir(exist_ok=True)
    cache = ROOT / "build/source-cache"
    cache.mkdir(parents=True, exist_ok=True)
    for row in rows:
        path = cache / row["name"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            with urllib.request.urlopen(row["url"], timeout=60) as response:
                data = response.read()
            if hashlib.sha256(data).hexdigest() != row["sha256"]:
                raise ValueError(f"Source snapshot hash mismatch: {row['name']}")
            path.write_bytes(data)
        shutil.copy2(path, dest / row["name"])
    (dest / "SOURCES.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")

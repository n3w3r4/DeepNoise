"""Check archive integrity, native inventory, notices and excluded local data."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

def verify(archive):
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() is not None:
            raise ValueError("ZIP integrity check failed")
        names = set(bundle.namelist())
        prefix = "DeepNoise/"
        for item in ("DeepNoise.exe", "LICENSE-MIT", "LICENSE-APACHE", "NOTICE", "docs/LICENSE_AUDIT.md",
                     "docs/README.pt-BR.md", "sources/SOURCES.json", "NATIVE_DEPENDENCIES.json",
                     "_internal/pystray/__init__.py", "_internal/ui/api.js"):
            if prefix + item not in names:
                raise ValueError(f"Missing release file: {item}")
        if any("asio.dll" in n.lower() or "krisp-rea" in n.lower() or n.endswith(("settings.json", ".wav")) for n in names):
            raise ValueError("Excluded binary or local data found in archive")
        manifest = json.loads(bundle.read(prefix + "NATIVE_DEPENDENCIES.json"))
        actual = {n for n in names if n.lower().endswith((".dll", ".pyd"))}
        declared = {prefix + item["path"] for item in manifest["binaries"]}
        if actual != declared:
            raise ValueError("Native inventory does not match archive")
        for item in manifest["binaries"]:
            data = bundle.read(prefix + item["path"])
            if len(data) != item["size"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise ValueError(f"Native hash mismatch: {item['path']}")
            for notice in item["notice_files"]:
                if prefix + notice not in names:
                    raise ValueError(f"Missing native notice: {notice}")
        for source in json.loads(bundle.read(prefix + "sources/SOURCES.json")):
            data = bundle.read(prefix + "sources/" + source["name"])
            if hashlib.sha256(data).hexdigest() != source["sha256"]:
                raise ValueError(f"Source snapshot hash mismatch: {source['name']}")
        print(f"Verified {len(manifest['binaries'])} native files, source snapshots and ZIP integrity.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    verify(parser.parse_args().archive)

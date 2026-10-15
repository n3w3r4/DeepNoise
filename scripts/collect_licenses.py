"""Collect installed distribution license files and versions for a release build."""
import importlib.metadata as metadata
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def collect(app_dir):
    dest = app_dir / "licenses"
    shutil.copytree(ROOT / "licenses", dest, dirs_exist_ok=True)
    inventory = []
    for dist in sorted(metadata.distributions(), key=lambda d: d.metadata["Name"].lower()):
        name = dist.metadata["Name"]
        copied = []
        for item in dist.files or []:
            if not any(word in Path(str(item)).name.lower() for word in ("license", "licence", "copying", "notice")):
                continue
            source = Path(dist.locate_file(item))
            if not source.is_file():
                continue
            # Use a flat, numbered name: wheel RECORD paths may contain ../ entries.
            target = dest / name / f"{len(copied):03d}-{source.name}"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied.append(target.relative_to(app_dir).as_posix())
        inventory.append({"name": name, "version": dist.version, "license_files": copied})
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.is_file():
        shutil.copy2(python_license, dest / "Python-LICENSE.txt")
    (app_dir / "DEPENDENCIES.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")

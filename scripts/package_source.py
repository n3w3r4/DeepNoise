"""Create a Git source archive and checksums after committing the reviewed tree."""
import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from version import VERSION

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist-dir", type=Path, default=ROOT / "dist")
    dest = parser.parse_args().dist_dir.resolve()
    dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
    if dirty:
        raise SystemExit("Commit the reviewed tree before creating its source archive.")
    dest.mkdir(parents=True, exist_ok=True)
    archive = dest / f"DeepNoise-{VERSION}-source.zip"
    subprocess.run(["git", "archive", "--format=zip", f"--prefix=DeepNoise-{VERSION}/",
                    "-o", str(archive), "HEAD"], cwd=ROOT, check=True)
    lines = []
    for p in sorted(dest.glob(f"DeepNoise-{VERSION}-*.zip")):
        with p.open("rb") as stream:
            lines.append(f"{hashlib.file_digest(stream, 'sha256').hexdigest()}  {p.name}")
    (dest / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(archive)

if __name__ == "__main__":
    main()

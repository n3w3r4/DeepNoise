"""Build dist/DeepNoise/DeepNoise.exe (PyInstaller, one-folder) and dist/DeepNoise-<version>-win64.zip.

  .venv\\Scripts\\python.exe build.py

Downloads missing vendor/ binaries first (scripts/fetch_deps.py). User data (settings, logs,
WebView2 storage) lives in %APPDATA%\\DeepNoise when frozen; the bundle itself is read-only
resources: ui/, vendor/deep_filter_ladspa.dll, livekit's FFI library, PortAudio, pywebview +
pythonnet (windows use the Edge WebView2 runtime that ships with Windows 10/11).
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
BUILD = ROOT / "build"
DIST = ROOT / "dist"


def main():
    BUILD.mkdir(exist_ok=True)
    subprocess.run([sys.executable, str(ROOT / "scripts" / "fetch_deps.py")], check=True)
    import desktop
    from version import VERSION

    ico = BUILD / "DeepNoise.ico"
    art = ROOT / "assets" / "icon-source.png"  # app artwork (headphones), 1254 px master
    desktop.save_ico(ico, art)
    desktop.app_icon(256, art).save(ROOT / "ui" / "icon.png")  # window/page icon and tray base
    sep = ";"  # PyInstaller --add-data separator on Windows
    cmd = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
        "--name", "DeepNoise", "--icon", str(ico),
        "--distpath", str(DIST), "--workpath", str(BUILD / "work"), "--specpath", str(BUILD),
        "--add-data", f"{ROOT / 'ui'}{sep}ui",
        "--add-data", f"{ROOT / 'vendor'}{sep}vendor",
        "--collect-all", "livekit",          # native FFI library + protobufs
        "--collect-all", "webview",          # pywebview (WebView2 via WinForms)
        "--collect-all", "clr_loader",       # pythonnet runtime loader
        "--collect-all", "pythonnet",
        "--collect-data", "sounddevice",     # bundled PortAudio DLL
        "--hidden-import", "pystray._win32",
        "--exclude-module", "tkinter",
        str(ROOT / "app.py"),
    ]
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)

    app_dir = DIST / "DeepNoise"
    for doc in ("README.md", "THIRD_PARTY_NOTICES.md", "LICENSE"):
        if (ROOT / doc).exists():
            shutil.copy2(ROOT / doc, app_dir / doc)
    shutil.copy2(ROOT / "scripts" / "install-drivers.ps1", app_dir / "install-drivers.ps1")
    size = sum(f.stat().st_size for f in app_dir.rglob("*") if f.is_file())
    zip_path = shutil.make_archive(str(DIST / f"DeepNoise-{VERSION}-win64"), "zip", DIST, "DeepNoise")
    print(f"\nOK: {app_dir / 'DeepNoise.exe'}  ({size / 1e6:.0f} MB na pasta)\nzip: {zip_path}")


if __name__ == "__main__":
    main()

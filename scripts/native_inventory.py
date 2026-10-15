"""Map packaged native binaries to provider notices; reject unknown additions."""
import hashlib
import json
from pathlib import Path

def notice_group(relative):
    p = Path(relative)
    name = p.name.lower()
    parts = [x.lower() for x in p.parts]
    if "asio" in name:
        raise ValueError(f"Unreviewed ASIO binary: {relative}")
    groups = {
        "vendor": "deepfilternet", "livekit": "livekit", "_sounddevice_data": "portaudio",
        "numpy": "numpy", "numpy.libs": "numpy", "scipy": "scipy", "scipy.libs": "scipy",
        "pil": "pillow", "google": "protobuf", "psutil": "psutil", "pythonnet": "pythonnet",
        "clr_loader": "clr_loader", "webview": "webview",
    }
    for part in parts:
        if part in groups:
            return groups[part]
    if name.startswith("_cffi_backend"):
        return "cffi"
    if len(parts) == 1 and (name.startswith(("api-ms-win-", "vcruntime", "python")) or name in {
        "ucrtbase.dll", "libffi-8.dll", "libssl-3.dll", "libcrypto-3.dll",
        "pyexpat.pyd", "select.pyd", "unicodedata.pyd", "_asyncio.pyd", "_bz2.pyd",
        "_ctypes.pyd", "_decimal.pyd", "_elementtree.pyd", "_hashlib.pyd", "_lzma.pyd",
        "_multiprocessing.pyd", "_overlapped.pyd", "_queue.pyd", "_socket.pyd", "_ssl.pyd",
        "_uuid.pyd", "_wmi.pyd", "_zstd.pyd",
    }):
        return "python"
    raise ValueError(f"No native notice mapping: {relative}")

def collect(app_dir):
    app_dir = Path(app_dir)
    groups = {
        "deepfilternet": ["licenses/DeepFilterNet-LICENSE-MIT.txt", "licenses/native/DeepFilterNet-Rust-NOTICES.txt"],
        "livekit": ["licenses/native/LiveKit-APACHE-2.0.txt", "licenses/native/LiveKit-NOTICE.txt", "licenses/native/LiveKit-Rust-NOTICES.txt", "licenses/native/libsoxr-LICENCE.txt", "licenses/native/LGPL-2.1.txt"],
        "portaudio": ["licenses/native/PortAudio-LICENSE.txt"],
        "webview": ["licenses/native/WebView2-LICENSE.txt", "licenses/native/WebView2-NOTICE.txt"],
        "python": ["licenses/Python-LICENSE.txt", "licenses/native/OpenSSL-LICENSE.txt", "licenses/native/libffi-LICENSE.txt", "licenses/native/expat-COPYING.txt", "licenses/native/xz-COPYING.txt", "licenses/native/zlib-ng-LICENSE.txt", "licenses/native/zstd-LICENSE.txt"],
    }
    for dist in ("numpy", "scipy", "pillow", "protobuf", "psutil", "pythonnet", "clr_loader", "cffi", "livekit", "pywebview"):
        files = sorted(p.relative_to(app_dir).as_posix() for p in (app_dir / "licenses" / dist).glob("*") if p.is_file())
        if not files:
            raise ValueError(f"Missing wheel license files: {dist}")
        key = "webview" if dist == "pywebview" else dist
        groups.setdefault(key, []).extend(files)
    inventory = []
    internal = app_dir / "_internal"
    for p in sorted(internal.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in (".dll", ".pyd"):
            continue
        relative = p.relative_to(internal)
        group = notice_group(relative)
        for license_path in groups[group]:
            if not (app_dir / license_path).is_file():
                raise ValueError(f"Missing notice: {license_path}")
        with p.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        inventory.append({"path": p.relative_to(app_dir).as_posix(), "size": p.stat().st_size,
                          "sha256": digest, "provider": group, "notice_files": groups[group]})
    result = {"scope": "Actual packaged DLL/PYD files; notice mapping is not licensing clearance.",
              "known_open_item": "LiveKit static LGPL/FFmpeg source and relink validation: docs/LICENSE_AUDIT.md",
              "binaries": inventory}
    (app_dir / "NATIVE_DEPENDENCIES.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result

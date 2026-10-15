"""DeepNoise uses Windows x64 WASAPI; omit unused ASIO and other architectures."""
from pathlib import Path
from PyInstaller.utils.hooks import get_module_file_attribute

base = Path(get_module_file_attribute("sounddevice")).parent
relative = Path("_sounddevice_data") / "portaudio-binaries"
library = base / relative / "libportaudio64bit.dll"
if not library.is_file():
    raise RuntimeError("The reviewed Windows x64 PortAudio DLL is missing")
binaries = [(str(library), str(relative))]
datas = [(str(base / relative / "README.md"), str(relative))]

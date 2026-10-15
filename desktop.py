"""Windows desktop integration: tray icon (pystray), app icon and start-with-Windows.
The app windows themselves live in windows.py (pywebview)."""

import ctypes as C
import sys
import threading
from pathlib import Path

# --- tray icon ------------------------------------------------------------------------------
ICON_SOURCE = None  # set by app.py: path of the app artwork (ui/icon.png)


def app_icon(size, source=None):
    """The app artwork (headphones) as a square icon with Windows 11-style rounded corners.
    Small sizes get a little unsharp mask so the engraving lines don't turn to mush."""
    from PIL import Image, ImageDraw, ImageFilter

    src = Image.open(source or ICON_SOURCE).convert("RGBA")
    big = src.resize((size * 4, size * 4), Image.LANCZOS)  # supersample, then mask, then downscale
    mask = Image.new("L", big.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, big.width - 1, big.height - 1], radius=int(big.width * 0.18), fill=255)
    big.putalpha(mask)
    img = big.resize((size, size), Image.LANCZOS)
    if size <= 48:
        img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=60, threshold=2))
    return img


def make_icon_image(state="on", size=64):
    """Tray icon: the app artwork plus status. on = red LED, wait = amber LED,
    off (unfiltered) = greyed, muted = greyed with a red slash."""
    from PIL import ImageDraw, ImageOps

    img = app_icon(size)
    if state in ("off", "muted"):
        alpha = img.getchannel("A")
        img = ImageOps.grayscale(img.convert("RGB")).convert("RGBA")
        img = img.point(lambda v: int(v * 0.75))
        img.putalpha(alpha)
    d = ImageDraw.Draw(img)
    s = size
    if state in ("on", "wait"):
        r = s * 0.17
        cx, cy = s - r - s * 0.02, s - r - s * 0.02
        d.ellipse([cx - r - s * 0.04, cy - r - s * 0.04, cx + r + s * 0.04, cy + r + s * 0.04], fill=(21, 24, 27, 255))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(226, 54, 44, 255) if state == "on" else (217, 138, 20, 255))
    if state == "muted":
        w = max(3, s // 9)
        d.line([s * 0.12, s * 0.88, s * 0.88, s * 0.12], fill=(21, 24, 27, 255), width=w + max(2, s // 16))
        d.line([s * 0.12, s * 0.88, s * 0.88, s * 0.12], fill=(226, 54, 44, 255), width=w)
    return img


def save_ico(path, source):
    sizes = (16, 20, 24, 32, 40, 48, 64, 128, 256)
    imgs = [app_icon(n, source) for n in sizes]
    imgs[-1].save(path, format="ICO", sizes=[(n, n) for n in sizes], append_images=imgs[:-1])


TRAY_TEXT = {
    "pt-BR": {"quick": "Ações rápidas", "open": "Abrir DeepNoise", "mute": "Mutar microfone", "nc": "Cancelar meu ruído",
              "quit": "Sair do DeepNoise", "tip_on": "DeepNoise: no ar", "tip_muted": "DeepNoise: mudo",
              "tip_off": "DeepNoise: sem filtro", "tip_wait": "DeepNoise: esperando dispositivo"},
    "en-US": {"quick": "Quick actions", "open": "Open DeepNoise", "mute": "Mute microphone", "nc": "Cancel my noise",
              "quit": "Quit DeepNoise", "tip_on": "DeepNoise: live", "tip_muted": "DeepNoise: muted",
              "tip_off": "DeepNoise: unfiltered", "tip_wait": "DeepNoise: waiting for device"},
}


def ui_lang(setting):
    if setting in TRAY_TEXT:
        return setting
    try:
        lid = C.windll.kernel32.GetUserDefaultUILanguage()
        return "pt-BR" if (lid & 0x3FF) == 0x16 else "en-US"  # LANG_PORTUGUESE
    except Exception:
        return "en-US"


class Tray:
    """pystray icon on its own thread. Callbacks receive no args and must be thread-safe."""

    def __init__(self, on_quick, on_open, on_mute, on_toggle_nc, on_quit, get_state):
        import pystray

        self.pystray = pystray
        self.get_state = get_state  # -> dict(lang, muted, enabled, status)
        self._last = None
        T = lambda k: (lambda item: TRAY_TEXT[ui_lang(self.get_state()["lang"])][k])
        M = pystray.MenuItem
        menu = pystray.Menu(
            M(T("quick"), lambda: on_quick(), default=True),
            M(T("open"), lambda: on_open()),
            pystray.Menu.SEPARATOR,
            M(T("mute"), lambda: on_mute(), checked=lambda item: self.get_state()["muted"]),
            M(T("nc"), lambda: on_toggle_nc(), checked=lambda item: self.get_state()["enabled"]),
            pystray.Menu.SEPARATOR,
            M(T("quit"), lambda: on_quit()),
        )
        self.icon = pystray.Icon("DeepNoise", make_icon_image("on"), "DeepNoise", menu)
        threading.Thread(target=self.icon.run, daemon=True, name="tray").start()

    def refresh(self):
        """Update icon/tooltip/menu when the state changed (call ~1 Hz)."""
        st = self.get_state()
        kind = "wait" if st["status"] != "running" else "muted" if st["muted"] else "on" if st["enabled"] else "off"
        key = (kind, st["lang"], st["muted"], st["enabled"])
        if key == self._last:
            return
        self._last = key
        txt = TRAY_TEXT[ui_lang(st["lang"])]
        self.icon.icon = make_icon_image(kind)
        self.icon.title = txt[{"on": "tip_on", "muted": "tip_muted", "off": "tip_off", "wait": "tip_wait"}[kind]]
        self.icon.update_menu()

    def stop(self):
        self.icon.stop()


# --- start with Windows -----------------------------------------------------------------------
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def autostart_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --tray'
    pyw = Path(sys.executable).with_name("pythonw.exe")
    return f'"{pyw}" "{Path(__file__).with_name("app.py")}" --tray'


def get_autostart():
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, "DeepNoise")
            return True
    except OSError:
        return False


def set_autostart(on):
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, "DeepNoise", 0, winreg.REG_SZ, autostart_command())
        else:
            try:
                winreg.DeleteValue(k, "DeepNoise")
            except OSError:
                pass

"""Native app windows (pywebview + WebView2): the main window and the tray flyout.

pywebview owns the main thread (webview.start()); every other part of the app runs on its own
thread and calls these methods, which pywebview marshals to the GUI thread.
"""

import ctypes as C
import time
from ctypes import wintypes

import webview

u32 = C.windll.user32
u32.GetForegroundWindow.restype = wintypes.HWND
u32.GetAncestor.restype = wintypes.HWND
u32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, C.c_void_p]
GA_ROOTOWNER = 3
SPI_GETWORKAREA = 0x30
DWMWA_WINDOW_CORNER_PREFERENCE, DWMWCP_ROUND = 33, 2


def _hwnd(win):
    try:
        return int(win.native.Handle.ToInt64())
    except Exception:
        return None


def _bring_to_front(h):
    """SetForegroundWindow only works for the process that got the last input. Temporarily attach to
    the foreground thread's input queue so the flyout can take focus however it was opened."""
    hw = wintypes.HWND(h)
    fg = u32.GetForegroundWindow()
    fg_thread = u32.GetWindowThreadProcessId(fg, None) if fg else 0
    me = C.windll.kernel32.GetCurrentThreadId()
    attached = bool(fg_thread and fg_thread != me and u32.AttachThreadInput(fg_thread, me, True))
    try:
        u32.BringWindowToTop(hw)
        u32.SetForegroundWindow(hw)
    finally:
        if attached:
            u32.AttachThreadInput(fg_thread, me, False)


def _work_area():
    wa = wintypes.RECT()
    u32.SystemParametersInfoW(SPI_GETWORKAREA, 0, C.byref(wa), 0)
    return wa


class Windows:
    MAIN_SIZE = (460, 860)
    FLY_SIZE = (360, 556)

    def __init__(self, url, start_hidden, on_quit):
        self.on_quit = on_quit
        self.quitting = False
        self.fly_shown_at = 0.0
        self.fly_hidden_at = 0.0
        self.fly_had_focus = False
        self.main = webview.create_window("DeepNoise", url, width=self.MAIN_SIZE[0], height=self.MAIN_SIZE[1],
                                          min_size=(400, 560), hidden=start_hidden, background_color="#2b2d30")
        self.main.events.closing += self._main_closing
        self.fly = webview.create_window("DeepNoise — quick", url + "flyout.html", width=self.FLY_SIZE[0],
                                         height=self.FLY_SIZE[1], frameless=True, on_top=True, resizable=False,
                                         hidden=True, easy_drag=False, focus=True, background_color="#2b2d30")
        self.fly.events.shown += lambda: self._round(self.fly)

    # --- main window --------------------------------------------------------------------------
    def _main_closing(self):
        """The X button hides the window; DeepNoise keeps running in the tray ."""
        if self.quitting:
            return True
        self.main.hide()
        return False

    def open_main(self):
        self.hide_flyout()
        self.main.show()
        self.main.restore()
        h = _hwnd(self.main)
        if h:
            _bring_to_front(h)

    # --- flyout -------------------------------------------------------------------------------
    @staticmethod
    def _round(win):
        h = _hwnd(win)
        if h:
            pref = C.c_int(DWMWCP_ROUND)
            C.windll.dwmapi.DwmSetWindowAttribute(wintypes.HWND(h), DWMWA_WINDOW_CORNER_PREFERENCE, C.byref(pref), C.sizeof(pref))

    def fly_visible(self):
        h = _hwnd(self.fly)
        return bool(h and u32.IsWindowVisible(wintypes.HWND(h)))

    def toggle_flyout(self):
        if self.fly_visible():
            self.hide_flyout()
        elif time.monotonic() - self.fly_hidden_at < 0.35:
            pass  # this tray click is what just took focus away and hid it: treat as "close"
        else:
            wa = _work_area()
            h = _hwnd(self.fly)
            k = (u32.GetDpiForWindow(wintypes.HWND(h)) if h else 96) / 96
            w, ht = self.FLY_SIZE
            self.fly.move(int(wa.right / k - w - 12), int(wa.bottom / k - ht - 12))
            self.fly.show()
            self.fly_shown_at = time.monotonic()
            self.fly_had_focus = False
            h = _hwnd(self.fly)
            if h:
                _bring_to_front(h)

    def hide_flyout(self):
        if self.fly_visible():
            self.fly.hide()
            self.fly_hidden_at = time.monotonic()

    def autohide(self):
        """Hide the flyout when focus goes elsewhere. Call often from a background loop."""
        if not self.fly_visible() or time.monotonic() - self.fly_shown_at < 0.4:
            return
        h = _hwnd(self.fly)
        fg = u32.GetForegroundWindow()
        if not fg or fg == h or u32.GetAncestor(fg, GA_ROOTOWNER) == h:
            self.fly_had_focus = True
            return  # the flyout or one of its popups (e.g. an open <select> list)
        if self.fly_had_focus:  # never vanish before the user could reach it
            self.hide_flyout()

    # --- lifecycle ----------------------------------------------------------------------------
    def quit(self):
        self.quitting = True
        for w in (self.fly, self.main):
            try:
                w.destroy()
            except Exception:
                pass

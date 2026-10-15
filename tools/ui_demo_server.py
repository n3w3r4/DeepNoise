"""Serve DeepNoise's ui/ with a fake engine API, for UI work and screenshots without audio devices.

  python tools/ui_demo_server.py [--port 8790] [--lang en-US|pt-BR]

Open http://127.0.0.1:8790/ (main window), /flyout.html (quick actions) or /_showcase.html (both
side by side, transitions off, for docs/images). Everything is demo data: no microphone or speaker is
opened and no settings are written. The meter stream runs for --stream-seconds per page and then ends,
so headless browsers can finish a screenshot (see docs/DEVELOPMENT.md).
"""

import argparse
import json
import math
import random
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

UI = Path(__file__).resolve().parent.parent / "ui"
TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript", ".png": "image/png"}

SHOWCASE = b"""<!doctype html>
<html><head><meta charset="utf-8"><style>
  html,body{margin:0;background:#1a1c1f}
  .stage{display:flex;gap:40px;align-items:flex-end;padding:40px 48px;width:max-content}
  iframe{border:0;border-radius:12px;box-shadow:0 18px 50px rgba(0,0,0,.55),0 0 0 1px rgba(255,255,255,.06);background:#2b2d30}
</style></head><body><div class="stage">
  <iframe src="/" width="440" height="1020" title="Main window"></iframe>
  <iframe src="/flyout.html" width="360" height="556" title="Quick actions"></iframe>
</div><script>
  for (const f of document.querySelectorAll("iframe")) f.addEventListener("load", () => {
    const s = f.contentDocument.createElement("style");
    s.textContent = "*{transition:none!important}";  // no switch caught mid-animation
    f.contentDocument.head.appendChild(s);
  });
</script></body></html>"""


def demo_state(lang):
    return {
        "devices": {
            "inputs": [{"name": "Microphone (USB Condenser Mic)", "raw": True, "cable": False},
                       {"name": "Headset Microphone (Wireless Headset)", "raw": True, "cable": False},
                       {"name": "Hi-Fi Cable Output (VB-Audio Hi-Fi Cable)", "raw": False, "cable": True}],
            "outputs": [{"name": "CABLE Input (VB-Audio Virtual Cable)", "cable": True},
                        {"name": "Headphones (Wireless Headset)", "cable": False},
                        {"name": "Speakers (Realtek Audio)", "cable": False}],
        },
        "selected": {"input": "Microphone (USB Condenser Mic)", "output": "CABLE Input (VB-Audio Virtual Cable)",
                     "monitor": "Headphones (Wireless Headset)",
                     "spk_input": "Hi-Fi Cable Output (VB-Audio Hi-Fi Cable)",
                     "spk_output": "Headphones (Wireless Headset)"},
        "settings": {"enabled": True, "level": 100, "pf": 0.02, "gate": -50, "hpf": 100, "monitor": False,
                     "aec": True, "bvc": False, "bvc_threshold": None, "spk_enabled": True, "spk_level": 100,
                     "lock_mic": None, "hotkey": True, "lang": lang},
        "status": "running", "running": True, "error": None, "waiting_for": None, "muted": False,
        "aec_available": True, "usage": {"mic": [], "voice": ["Discord"], "spk": ["Discord"]},
        "voice_device": "CABLE Output (VB-Audio Virtual Cable)", "mic_volume": [80, 0.0, False],
        "hotkey_ok": True, "autostart": True,
    }


def demo_meters(t):
    """Speech bursts over a room-noise floor; the clean voice keeps the speech and drops the noise."""
    speech = (t % 4.0) < 2.4
    syllables = -20 - 9 * abs(math.sin(t * 9)) if speech else -120
    noise = -50 + 3 * math.sin(t * 23) + random.random() * 2
    return {"in_db": max(noise, syllables), "out_db": syllables - 1 if speech else -86 + random.random() * 3,
            "spk_in_db": -32 + 6 * math.sin(t * 3), "spk_out_db": -34 + 6 * math.sin(t * 3),
            "xruns": 0, "running": True, "status": "running", "muted": False, "waiting_for": None}


def make_handler(state, stream_seconds):
    streamed = set()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def _send(self, body, ctype, code=200):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/api/state":
                return self._send(json.dumps(state).encode(), "application/json")
            if path == "/api/meters":
                page = self.headers.get("Referer", "")
                if page in streamed:
                    return self._send(b"", "text/plain", 204)  # EventSource stops reconnecting on 204
                streamed.add(page)
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                try:
                    for _ in range(int(stream_seconds * 20)):
                        self.wfile.write(f"data: {json.dumps(demo_meters(time.time()))}\n\n".encode())
                        self.wfile.flush()
                        time.sleep(0.05)
                except OSError:
                    pass
                return None
            if path == "/_showcase.html":
                return self._send(SHOWCASE, TYPES[".html"])
            f = UI / ("index.html" if path == "/" else path.lstrip("/"))
            if f.is_file() and f.resolve().parent == UI:
                return self._send(f.read_bytes(), TYPES.get(f.suffix, "application/octet-stream"))
            return self._send(b"{}", "application/json", 404)

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            data = json.loads(self.rfile.read(length) or b"{}")
            if self.path == "/api/settings":
                state["settings"].update({k: v for k, v in data.items() if k in state["settings"]})
            elif self.path == "/api/mute":
                state["muted"] = not state["muted"]
            return self._send(json.dumps(state).encode(), "application/json")

    return Handler


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8790)
    ap.add_argument("--lang", default="en-US", choices=["en-US", "pt-BR"])
    ap.add_argument("--stream-seconds", type=float, default=4.0, help="meter stream length per page")
    args = ap.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(demo_state(args.lang), args.stream_seconds))
    print(f"DeepNoise UI demo (no audio): http://127.0.0.1:{args.port}/  /flyout.html  /_showcase.html")
    server.serve_forever()


if __name__ == "__main__":
    main()

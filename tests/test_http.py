"""Exercise the real handler without constructing App or opening audio devices."""
import http.client
import threading
import unittest
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import Mock, patch
import app

class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fake = SimpleNamespace(state=lambda: {"status": "running"}, quit=Mock())
        cls.patcher = patch.object(app, "APP", cls.fake)
        cls.patcher.start()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.patcher.stop()

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection(*self.server.server_address, timeout=3)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            response = conn.getresponse()
            return response.status, response.read()
        finally:
            conn.close()

    def test_static_and_state(self):
        for path in ("/", "/flyout.html", "/api.js", "/i18n.js", "/api/state"):
            with self.subTest(path=path):
                code, body = self.request("GET", path)
                self.assertEqual(code, 200)
                self.assertTrue(body)

    def test_browser_attack_cannot_quit(self):
        self.fake.quit.reset_mock()
        code, _ = self.request("POST", "/api/quit", "{}", {"Origin": "https://example.org"})
        self.assertEqual(code, 403)
        self.fake.quit.assert_not_called()

    def test_valid_empty_action(self):
        self.fake.quit.reset_mock()
        code, _ = self.request("POST", "/api/quit", headers={
            "Content-Type": "application/json", "X-DeepNoise-Request": "1"})
        self.assertEqual(code, 200)
        self.fake.quit.assert_called_once()

    def test_bad_json_returns_400(self):
        code, _ = self.request("POST", "/api/quit", "{", {
            "Content-Type": "application/json", "X-DeepNoise-Request": "1"})
        self.assertEqual(code, 400)

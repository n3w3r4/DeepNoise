import io
import unittest
from local_api import allowed_request, read_json_body, MAX_BODY

class RequestValidationTests(unittest.TestCase):
    def setUp(self):
        self.headers = {"Host": "127.0.0.1:1234", "Content-Type": "application/json",
                        "X-DeepNoise-Request": "1"}

    def test_local_clients_and_same_origin_browser(self):
        self.assertTrue(allowed_request(self.headers, 1234, "POST"))
        self.headers["Origin"] = "http://127.0.0.1:1234"
        self.assertTrue(allowed_request(self.headers, 1234, "POST"))

    def test_cross_origin_and_rebinding(self):
        for changes in ({"Origin": "https://example.org"}, {"Origin": "null"},
                        {"Host": "attacker.example:1234"}, {"Host": "127.0.0.1:9999"},
                        {"Sec-Fetch-Site": "cross-site"}):
            for method in ("GET", "POST"):
                with self.subTest(changes=changes, method=method):
                    self.assertFalse(allowed_request({**self.headers, **changes}, 1234, method))

    def test_post_requires_custom_header(self):
        del self.headers["X-DeepNoise-Request"]
        self.assertFalse(allowed_request(self.headers, 1234, "POST"))
        self.assertTrue(allowed_request(self.headers, 1234, "GET"))

    def test_json_object_and_empty_action(self):
        self.assertEqual(read_json_body(self.headers, io.BytesIO()), {})
        self.headers["Content-Length"] = "12"
        self.assertEqual(read_json_body(self.headers, io.BytesIO(b'{"level":50}')), {"level": 50})

    def test_invalid_bodies(self):
        for body in (b'[]', b'null', b'"text"', b'{', b'\xff'):
            with self.subTest(body=body), self.assertRaises(ValueError):
                read_json_body({**self.headers, "Content-Length": str(len(body))}, io.BytesIO(body))

    def test_oversize_and_invalid_lengths_rejected_before_read(self):
        for length in ("-1", "invalid", str(MAX_BODY + 1)):
            with self.subTest(length=length), self.assertRaises(ValueError):
                read_json_body({**self.headers, "Content-Length": length}, None)

    def test_content_type_and_transfer_encoding(self):
        for changes in ({"Content-Type": "text/plain"}, {"Transfer-Encoding": "chunked"}):
            with self.assertRaises(ValueError):
                read_json_body({**self.headers, **changes}, io.BytesIO())

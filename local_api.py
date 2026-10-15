"""Browser-origin protection and bounded JSON parsing for the loopback control API."""
import json

MAX_BODY = 64 * 1024

def allowed_request(headers, port, method):
    authority = f"127.0.0.1:{port}"
    if headers.get("Host") != authority:
        return False
    if headers.get("Origin") not in (None, f"http://{authority}"):
        return False
    if headers.get("Sec-Fetch-Site") == "cross-site":
        return False
    return method != "POST" or headers.get("X-DeepNoise-Request") == "1"

def read_json_body(headers, stream):
    if headers.get("Transfer-Encoding"):
        raise ValueError("transfer encoding is not supported")
    if headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
        raise ValueError("expected application/json")
    try:
        length = int(headers.get("Content-Length", "0"))
    except ValueError:
        raise ValueError("invalid content length") from None
    if not 0 <= length <= MAX_BODY:
        raise ValueError("request body is too large or has a negative length")
    try:
        data = json.loads(stream.read(length) or b"{}")
    except (ValueError, UnicodeDecodeError):
        raise ValueError("invalid JSON") from None
    if not isinstance(data, dict):
        raise ValueError("expected a JSON object")
    return data

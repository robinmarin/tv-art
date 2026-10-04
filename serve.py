"""Serve the Frame Art page and push images to the TV.

Run: .venv/bin/python serve.py, then open http://localhost:8000
"""
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

from samsungtvws.art import SamsungTVArt

TV_IP = os.environ.get("TV_IP", "192.168.68.56")  # set a DHCP reservation so this stays put
PORT = 8000
HERE = os.path.dirname(os.path.abspath(__file__))
MAX_BYTES = 20 * 1024 * 1024  # Frame's upload limit


def send_to_tv(jpeg: bytes) -> str:
    art = SamsungTVArt(TV_IP, port=8002, token_file=os.path.join(HERE, "tv-token.txt"),
                       name="FrameArt", timeout=30)
    try:
        content_id = art.upload(jpeg, file_type="JPEG", matte="none")
        art.select_image(content_id, show=True)
        return content_id
    finally:
        art.close()


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, body, ctype="text/plain"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != "/":
            return self.reply(404, b"not found")
        with open(os.path.join(HERE, "index.html"), "rb") as f:
            self.reply(200, f.read(), "text/html; charset=utf-8")

    def do_POST(self):
        # Only our own page may post, so other sites can't push images to the TV.
        if self.path != "/send" or self.headers.get("Origin") not in (None, f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}"):
            return self.reply(403, b"forbidden")
        size = int(self.headers.get("Content-Length", 0))
        if not 0 < size <= MAX_BYTES:
            return self.reply(413, b"image must be under 20 MB")
        try:
            self.reply(200, send_to_tv(self.rfile.read(size)).encode())
        except Exception as e:
            self.reply(502, f"{type(e).__name__}: {e}".encode())


if __name__ == "__main__":
    print(f"http://localhost:{PORT}  ->  TV at {TV_IP}")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()

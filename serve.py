"""Serve the Frame Art page and push images to the TV.

Run: .venv/bin/python serve.py, then open http://localhost:8000
"""
import html
import ipaddress
import json
import os
import socket
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse
from urllib.request import ProxyHandler, build_opener

from samsungtvws.art import SamsungTVArt

PORT = 8000
HERE = os.path.dirname(os.path.abspath(__file__))
MAX_BYTES = 20 * 1024 * 1024  # Frame's upload limit
# urlopen's macOS proxy lookup serialises the scan threads (1s -> 12s), and LAN traffic needs no proxy.
no_proxy = build_opener(ProxyHandler({}))


def frame_info(ip: str) -> dict | None:
    try:
        with no_proxy.open(f"http://{ip}:8001/api/v2/", timeout=1) as r:
            device = json.load(r)["device"]
    except (OSError, ValueError, KeyError):
        return None
    if device.get("FrameTVSupport") == "true":
        return {"ip": ip, "name": html.unescape(device.get("name", "Frame TV"))}
    return None


def find_tvs() -> list[dict]:
    """Ask every address on our subnet for Samsung's TV info and return the Frames."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("239.255.255.250", 1900))  # sends nothing, just picks the LAN interface
        prefix = s.getsockname()[0].rsplit(".", 1)[0]
    # ponytail: scans our /24 only, type the IP in the page if the TV sits elsewhere on a wider subnet
    with ThreadPoolExecutor(254) as pool:
        return [tv for tv in pool.map(frame_info, (f"{prefix}.{i}" for i in range(1, 255))) if tv]


def send_to_tv(ip: str, jpeg: bytes, log) -> None:
    log(f"Connecting to {ip}. If the TV asks to allow FrameArt, accept with the remote")
    # This TV remembers the approval itself; other firmware hands out a token, kept here.
    art = SamsungTVArt(ip, port=8002, token_file=os.path.join(HERE, "tv-token.txt"),
                       name="FrameArt", timeout=30)
    try:
        art.open()
        log(f"Connected, uploading {len(jpeg) / 1e6:.1f} MB and waiting for the TV to store it")
        content_id = art.upload(jpeg, file_type="JPEG", matte="none")
        log(f"Stored as {content_id}, putting it on screen")
        art.select_image(content_id, show=True)
    finally:
        art.close()


def is_lan_ip(value: str) -> bool:
    try:
        return ipaddress.ip_address(value).is_private
    except ValueError:
        return False


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, body, ctype="text/plain"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            with open(os.path.join(HERE, "index.html"), "rb") as f:
                return self.reply(200, f.read(), "text/html; charset=utf-8")
        if self.path == "/tvs":
            return self.reply(200, json.dumps(find_tvs()).encode(), "application/json")
        self.reply(404, b"not found")

    def do_POST(self):
        url = urlparse(self.path)
        # Only our own page may post, so other sites can't push images to the TV.
        if url.path != "/send" or self.headers.get("Origin") not in (None, f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}"):
            return self.reply(403, b"forbidden")
        ip = parse_qs(url.query).get("tv", [""])[0]
        if not is_lan_ip(ip):
            return self.reply(400, b"pick a TV on your local network")
        size = int(self.headers.get("Content-Length", 0))
        if not 0 < size <= MAX_BYTES:
            return self.reply(413, b"image must be under 20 MB")
        jpeg = self.rfile.read(size)
        # Stream one line per step so the page can show progress. The connection
        # closes when we return (HTTP/1.0), which ends the stream.
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("X-Content-Type-Options", "nosniff")  # stops browsers buffering to sniff
        self.end_headers()

        def log(msg):
            self.wfile.write(f"{msg}\n".encode())

        try:
            send_to_tv(ip, jpeg, log)
            log("DONE")
        except Exception as e:
            log(f"ERROR {type(e).__name__}: {e}")


if __name__ == "__main__":
    print(f"http://localhost:{PORT}")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()

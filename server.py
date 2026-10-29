#!/usr/bin/env python3
"""Radar Dashboard - tiny local server (Python standard library only, nothing to install).

Serves index.html and proxies the live ADS-B feed:
the browser blocks direct calls to adsb.lol (no CORS headers), so the page
asks this server at /api/point and the server does the fetch instead.

Run:  python3 server.py          (then open http://localhost:8765)
      python3 server.py 9000     (custom port)
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "radar-dashboard-local/1.0"}


def fetch_json(url, timeout=12):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def get_traffic(lat, lon, radius_km):
    """Return (json_bytes, source_name). adsb.lol first, adsb.fi as fallback."""
    nm = radius_km / 1.852  # the feeds take radius in nautical miles
    sources = [
        ("adsb.lol", f"https://api.adsb.lol/v2/point/{lat}/{lon}/{nm:.2f}"),
        ("adsb.fi", f"https://opendata.adsb.fi/api/v2/lat/{lat}/lon/{lon}/dist/{nm:.2f}"),
    ]
    errors = []
    for name, url in sources:
        try:
            return fetch_json(url), name
        except Exception as e:  # noqa: BLE001 - report and try the next source
            errors.append(f"{name}: {e}")
    raise RuntimeError("; ".join(errors))


# Last good response per (lat, lon, radius). A refresh should be fast and
# should never come back empty-handed just because a feed hiccuped, so:
# serve a fresh copy for a few seconds, and if both feeds fail, serve the
# last good copy (marked stale) instead of an error.
CACHE = {}
CACHE_TTL_S = 10
STALE_TTL_S = 300


def get_traffic_cached(lat, lon, radius_km):
    """Return (json_bytes, source_name, cache_hit)."""
    key = (round(lat, 3), round(lon, 3), round(radius_km, 1))
    now = time.time()
    hit = CACHE.get(key)
    if hit and now - hit[0] < CACHE_TTL_S:
        return hit[1], hit[2], True
    try:
        body, source = get_traffic(lat, lon, radius_km)
        CACHE[key] = (now, body, source)
        return body, source, False
    except RuntimeError:
        if hit and now - hit[0] < STALE_TTL_S:
            return hit[1], hit[2] + " (stale)", True
        raise


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # keep the console quiet
        pass

    def send_bytes(self, code, body, content_type, extra_headers=None):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            with open(os.path.join(HERE, "index.html"), "rb") as f:
                self.send_bytes(200, f.read(), "text/html; charset=utf-8")
            return
        if parsed.path == "/api/point":
            q = parse_qs(parsed.query)
            try:
                lat = float(q["lat"][0])
                lon = float(q["lon"][0])
                radius_km = float(q.get("radiusKm", ["25"])[0])
                if not (-90 <= lat <= 90 and -180 <= lon <= 180 and 0 < radius_km <= 500):
                    raise ValueError("out of range")
            except (KeyError, IndexError, ValueError):
                self.send_bytes(400, b'{"error":"bad lat/lon/radiusKm"}', "application/json")
                return
            try:
                body, source, cached = get_traffic_cached(lat, lon, radius_km)
                headers = {"X-Data-Source": source, "X-Cache": "HIT" if cached else "MISS"}
                self.send_bytes(200, body, "application/json", headers)
            except RuntimeError as e:
                body = json.dumps({"error": str(e)}).encode()
                self.send_bytes(502, body, "application/json")
            return
        self.send_bytes(404, b"not found", "text/plain")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Radar Dashboard running at http://localhost:{port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

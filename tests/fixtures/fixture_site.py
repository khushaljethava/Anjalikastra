"""A tiny in-process HTTP server used as a crawl target for the tool's own tests.

Not part of the shipped tool — this is a fixture standing in for a real website so
the pipeline can be exercised end-to-end without hitting the network.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_PAGES: dict[str, str] = {
    "/": """<html><head><title>Fixture Home</title></head><body>
        <nav><a href="/">Home</a><a href="/about">About</a><a href="/login">Login</a><a href="/products">Products</a></nav>
        <h1>Welcome to the fixture site</h1>
        <p>This is a small site used to test Anjalikastra.</p>
    </body></html>""",
    "/about": """<html><head><title>About</title></head><body>
        <nav><a href="/">Home</a></nav>
        <h1>About us</h1>
        <article><p>We make fixtures.</p></article>
    </body></html>""",
    "/login": """<html><head><title>Login</title></head><body>
        <nav><a href="/">Home</a></nav>
        <h1>Log in</h1>
        <form method="post" action="/login">
            <input type="email" name="email" required>
            <input type="password" name="password" required>
            <button type="submit">Log in</button>
        </form>
    </body></html>""",
    "/products": """<html><head><title>Products</title></head><body>
        <nav><a href="/">Home</a></nav>
        <h1>Products</h1>
        <ul>
        <li><a href="/products/1">Widget</a></li>
        <li><a href="/products/2">Gadget</a></li>
        <li><a href="/products/3">Gizmo</a></li>
        <li><a href="/products/4">Doohickey</a></li>
        <li><a href="/products/5">Thingamajig</a></li>
        <li><a href="/products/6">Contraption</a></li>
        <li><a href="/products/7">Whatsit</a></li>
        <li><a href="/products/8">Doodad</a></li>
        <li><a href="/products/9">Gubbins</a></li>
        </ul>
    </body></html>""",
}

_PRODUCT_DETAIL = """<html><head><title>Product {pid}</title></head><body>
    <nav><a href="/">Home</a></nav>
    <h1>Product {pid}</h1>
    <div id="detail">loading</div>
    <script>
        fetch('/api/products/{pid}')
            .then((r) => r.json())
            .then((d) => {{ document.getElementById('detail').textContent = d.name; }});
    </script>
</body></html>"""

_SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}
</urlset>"""

_ROBOTS = "User-agent: *\nAllow: /\n"

_PRODUCTS = {
    "1": {"id": 1, "name": "Widget", "price": 9.99},
    "2": {"id": 2, "name": "Gadget", "price": 19.99},
}


class FixtureHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A002 - silence default request logging
        pass

    def do_GET(self):  # noqa: N802 - required BaseHTTPRequestHandler method name
        base = f"http://{self.headers.get('Host', 'localhost')}"

        if self.path == "/robots.txt":
            self._send(200, _ROBOTS, "text/plain")
        elif self.path == "/sitemap.xml":
            urls = "\n".join(f"<url><loc>{base}{p}</loc></url>" for p in _PAGES)
            self._send(200, _SITEMAP.format(urls=urls), "application/xml")
        elif self.path in _PAGES:
            self._send(200, _PAGES[self.path], "text/html")
        elif self.path.startswith("/products/"):
            pid = self.path.rsplit("/", 1)[-1]
            if pid in _PRODUCTS:
                self._send(200, _PRODUCT_DETAIL.format(pid=pid), "text/html")
            else:
                self._send(404, "<h1>Not found</h1>", "text/html")
        elif self.path.startswith("/api/products/"):
            pid = self.path.rsplit("/", 1)[-1]
            if pid in _PRODUCTS:
                self._send(200, json.dumps(_PRODUCTS[pid]), "application/json")
            else:
                self._send(404, json.dumps({"error": "not found"}), "application/json")
        elif self.path == "/api/products":
            self._send(200, json.dumps(list(_PRODUCTS.values())), "application/json")
        else:
            self._send(404, "<h1>Not found</h1>", "text/html")

    def _send(self, status: int, body: str, content_type: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class FixtureSite:
    def __init__(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
        self.port = self.server.server_address[1]
        self.base_url = f"http://127.0.0.1:{self.port}"
        self._thread: threading.Thread | None = None

    def start(self) -> "FixtureSite":
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()

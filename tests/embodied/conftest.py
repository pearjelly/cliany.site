"""pyright: reportMissingImports=false"""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from itertools import count
from pathlib import Path
from threading import Thread

import pytest  # type: ignore[import-not-found]


@pytest.fixture
def local_server():
    root = Path(__file__).parent / "pages"

    handler = partial(SimpleHTTPRequestHandler, directory=root)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.fixture
def benchmark_server():
    root = Path(__file__).parent / "pages"
    sequence = count(1)

    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path.split("?", 1)[0] != "/semantic_reorder.html":
                return super().do_GET()
            page = (root / "semantic_reorder.html").read_bytes()
            body = page.replace(b"__SHIFT__", str(next(sequence)).encode("ascii"))
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=root))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()

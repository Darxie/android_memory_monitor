"""Serve the dashboard locally on http://localhost:8000."""
import http.server
import webbrowser
from pathlib import Path

PORT = 8000


def main():
    dashboard_root = Path(__file__).resolve().parent
    handler = http.server.SimpleHTTPRequestHandler

    # Threaded: a single-threaded server stalls every other browser while one
    # keeps an idle keep-alive/preconnect socket open.
    with http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler) as httpd:
        url = f"http://localhost:{PORT}/index.html"
        print(f"Serving {dashboard_root} on {url}")
        print("Press Ctrl+C to stop.")
        webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    import os
    os.chdir(Path(__file__).resolve().parent)
    main()

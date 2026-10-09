"""One-time YouTube login. Run this on YOUR LAPTOP (it opens a browser), not on the VPS.

  python scripts/youtube_auth.py CLIENT_ID CLIENT_SECRET

It prints YT_REFRESH_TOKEN — paste it into the VPS .env. Only needs Python 3 (no packages).
"""
import json
import secrets
import sys
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8765
REDIRECT = f"http://127.0.0.1:{PORT}"
SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube"


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    client_id, client_secret = sys.argv[1], sys.argv[2]
    state = secrets.token_urlsafe(16)
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client_id, "redirect_uri": REDIRECT, "response_type": "code", "scope": SCOPES,
        "access_type": "offline", "prompt": "consent", "state": state})
    got = {}

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            got.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<h2>Done. Terminal pe wapas jao.</h2>".encode())

        def log_message(self, *a):
            pass

    print("Browser khul raha hai. Apne YouTube channel wale Google account se login karo...")
    print("Agar browser na khule to ye link kholo:\n" + url)
    webbrowser.open(url)
    srv = HTTPServer(("127.0.0.1", PORT), H)
    while "code" not in got and "error" not in got:
        srv.handle_request()
    if got.get("state") != state or "code" not in got:
        print("Login failed:", got.get("error"))
        sys.exit(1)
    data = urllib.parse.urlencode({"code": got["code"], "client_id": client_id, "client_secret": client_secret,
                                   "redirect_uri": REDIRECT, "grant_type": "authorization_code"}).encode()
    tok = json.loads(urllib.request.urlopen("https://oauth2.googleapis.com/token", data).read())
    print("\nYe .env mein daalo:\n")
    print(f"YT_CLIENT_ID={client_id}\nYT_CLIENT_SECRET={client_secret}\nYT_REFRESH_TOKEN={tok['refresh_token']}")


if __name__ == "__main__":
    main()

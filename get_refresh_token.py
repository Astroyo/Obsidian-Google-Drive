#!/usr/bin/env python3
"""
Usage: python get_refresh_token.py <clientID> <clientSecret>

Opens a local web server on port 80. Visit http://localhost to begin the
Google OAuth2 flow. The refresh token is printed once obtained, then the
server shuts itself down.

Note: port 80 may require sudo on Linux/macOS. If so, run with:
    sudo python get_refresh_token.py <clientID> <clientSecret>
"""

import sys
import json
import threading
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 80
REDIRECT_URI = "http://localhost"


def exchange_code_for_token(code, client_id, client_secret):
    payload = urllib.parse.urlencode({
        "code":          code,
        "client_id":     client_id,
        "client_secret": client_secret,
        "redirect_uri":  REDIRECT_URI,
        "grant_type":    "authorization_code",
    }).encode()

    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=payload,
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def make_handler(client_id, client_secret, server_ref):

    class OAuthHandler(BaseHTTPRequestHandler):

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)

            # Step 2: Google redirected back with ?code=...
            if "code" in params:
                code = params["code"][0]
                try:
                    token = exchange_code_for_token(code, client_id, client_secret)
                except Exception as e:
                    self._respond(500, f"<h2>Token exchange failed</h2><pre>{e}</pre>")
                    return

                refresh_token = token.get("refresh_token", "-")
                expires_in    = token.get("expires_in", 0)
                mins, secs    = divmod(expires_in, 60)

                self._respond(200, "<h2>Done! You can close this tab.</h2>")

                print("\n╔══════════════════════════════════════════╗")
                print("║          OAuth2 Credentials              ║")
                print("╠══════════════════════════════════════════╣")
                print(f"║  Client ID     : {client_id}")
                print(f"║  Client Secret : {client_secret}")
                print(f"║  Refresh Token : {refresh_token}")
                print(f"║  Access Token expires in: {mins}m {secs}s ({expires_in}s)")
                print("╚═══════════════════════════════════════════\n")

                # Shut down without deadlocking the handler thread
                threading.Thread(target=server_ref[0].shutdown, daemon=True).start()

            # Step 1: First visit -> redirect to Google consent screen
            else:
                auth_url = (
                    "https://accounts.google.com/o/oauth2/v2/auth"
                    f"?client_id={urllib.parse.quote(client_id)}"
                    f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
                    "&response_type=code"
                    "&scope=https://www.googleapis.com/auth/drive"
                    "&access_type=offline"
                    "&prompt=consent"
                )
                self.send_response(302)
                self.send_header("Location", auth_url)
                self.end_headers()

        def _respond(self, status, html):
            body = html.encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass  # silence request logs

    return OAuthHandler


def main():
    if len(sys.argv) != 3:
        print("Usage: python get_refresh_token.py <clientID> <clientSecret>")
        sys.exit(1)

    client_id, client_secret = sys.argv[1], sys.argv[2]

    # Use a mutable container so the handler closure can reference the server
    server_ref = [None]
    server_ref[0] = HTTPServer(("localhost", PORT), make_handler(client_id, client_secret, server_ref))

    print(f"-> Open http://localhost in your browser to begin.\n")
    server_ref[0].serve_forever()
    print("Server shut down. Bye!")


if __name__ == "__main__":
    main()
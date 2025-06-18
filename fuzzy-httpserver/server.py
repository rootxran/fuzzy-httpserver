import http.server
import socketserver
import os
import argparse
from urllib.parse import unquote
import difflib

class FuzzyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        requested = unquote(self.path.lstrip("/"))

        # List all files in current directory
        files = [f for f in os.listdir('.') if os.path.isfile(f)]

        # Exact match
        if requested in files:
            return super().do_GET()

        # Fuzzy match: prefix match first
        matched = [f for f in files if f.startswith(requested)]
        if not matched:
            # Fuzzy match: close match
            matched = difflib.get_close_matches(requested, files, n=1, cutoff=0.5)

        if matched:
            self.path = "/" + matched[0]
            print(f"[+] Fuzzy matched '{requested}' -> '{matched[0]}'")
            return super().do_GET()

        # No match: return text listing of available files
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

        self.wfile.write(b"[!] File not found. Available files:\n\n")
        for f in files:
            self.wfile.write(f"- {f}\n".encode())

parser = argparse.ArgumentParser(description="Fuzzy HTTP File Server")
parser.add_argument("-p", "--port", type=int, default=8000, help="Port to serve on (default: 8000)")
parser.add_argument("-d", "--directory", type=str, default=os.getcwd(), help="Directory to serve (default: current directory)")
args = parser.parse_args()

os.chdir(args.directory)

with socketserver.TCPServer(("", args.port), FuzzyHTTPRequestHandler) as httpd:
    print(f"[+] Serving '{args.directory}' on port {args.port}")
    httpd.serve_forever()


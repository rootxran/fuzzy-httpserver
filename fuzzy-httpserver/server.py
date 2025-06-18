import http.server
import socketserver
import os
import argparse
from urllib.parse import unquote
import difflib

class FuzzyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        requested = unquote(self.path.lstrip("/"))
        full_base = os.getcwd()
        path_parts = requested.split("/")
        base_path = full_base
        remaining_parts = path_parts.copy()

        # Step 1: Resolve intermediate fuzzy directories (case-insensitive)
        for i, part in enumerate(path_parts[:-1]):
            dirs = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
            mapping = {d.lower(): d for d in dirs}
            match = difflib.get_close_matches(part.lower(), mapping.keys(), n=1, cutoff=0.5)
            if match:
                real = mapping[match[0]]
                base_path = os.path.join(base_path, real)
                remaining_parts[i] = real
            else:
                break  # can't go deeper

        # Step 2: Handle final part (file or dir)
        final_part = path_parts[-1]
        try:
            entries = os.listdir(base_path)
        except Exception:
            entries = []

        mapping = {e.lower(): e for e in entries}
        full_target = os.path.join(base_path, mapping.get(final_part.lower(), final_part))

        if os.path.exists(full_target):
            remaining_parts[-1] = mapping.get(final_part.lower(), final_part)
            self.path = "/" + "/".join(remaining_parts)
            return super().do_GET()

        # Step 3: Try fuzzy match on final part
        matched = []
        candidates = list(mapping.keys())
        prefix_matches = [k for k in candidates if k.startswith(final_part.lower())]
        if prefix_matches:
            matched = [mapping[prefix_matches[0]]]
        else:
            fuzzy = difflib.get_close_matches(final_part.lower(), candidates, n=1, cutoff=0.5)
            if fuzzy:
                matched = [mapping[fuzzy[0]]]

        if matched:
            remaining_parts[-1] = matched[0]
            self.path = "/" + "/".join(remaining_parts)
            print(f"[+] Fuzzy matched '{requested}' -> '{self.path}'")
            return super().do_GET()

        # Step 4: No match — list available entries in that directory
        self.send_response(206) # for partial content because can't find the file but gives out the list of files
        self.send_header("Content-type", "text/plain")
        self.send_header("Server-Reply", "No file matched, Sending file list")
        self.end_headers()
        print(f"[!] No exact or fuzzy match for '{requested}'. Sending directory file list instead.")

        rel_path = "/" + "/".join(remaining_parts[:-1])
        self.wfile.write(f"[!] '{final_part}' not found in {rel_path or '/'}\n\n".encode())
        
        output = f"[>] Available entries in {rel_path or '/'}:\n\n".encode()
        self.wfile.write(output)
        print(output.decode().strip())
        print()

        for f in sorted(entries):
            full_rel = os.path.join(rel_path, f).replace("\\", "/")
            output = f"{full_rel}\n".encode()
            self.wfile.write(output)
            print(output.decode().strip())

parser = argparse.ArgumentParser(description="Fuzzy HTTP File Server")
parser.add_argument("-p", "--port", type=int, default=8000, help="Port to serve on (default: 8000)")
parser.add_argument("-d", "--directory", type=str, default=os.getcwd(), help="Directory to serve (default: current directory)")
args = parser.parse_args()

os.chdir(args.directory)

with socketserver.TCPServer(("", args.port), FuzzyHTTPRequestHandler) as httpd:
    print(f"[+] Serving '{args.directory}' on port {args.port}")
    httpd.serve_forever()

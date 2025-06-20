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
            print(f"\033[92m[+] Fuzzy matched '{requested}' -> '{self.path}'\033[0m")
            return super().do_GET()

        # Step 4: No match — 404 response and list dirs on server side
        self.send_response(404)
        self.send_header("Content-type", "text/plain")
        self.send_header("Server-Reply", "No file matched.")
        self.end_headers()
        print(f"\033[91m[!] No exact or fuzzy match for '{requested}'.\033[0m")

        rel_path = "/" + "/".join(remaining_parts[:-1])
        abs_dir = os.path.join(self.directory, *remaining_parts[:-1])
        
        print(f"\033[95m[>] Available entries in {rel_path or '/'}:\033[0m\n")

        for f in sorted(entries):
            full_rel = os.path.join(rel_path, f).replace("\\", "/")
            abs_path = os.path.join(abs_dir, f)
            if os.path.isdir(abs_path):
                print(f"\033[94m{full_rel} (D)\033[0m")
            else:
                print(full_rel)

        print("\n") # for giving some gap in output

    def do_POST(self):
        requested = unquote(self.path.lstrip("/"))
        path_parts = requested.split("/")
        filename = path_parts[-1] or "default"

        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
        except Exception as e:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"[!] Failed to read POST data.\n")
            print(f"[!] Error reading POST data: {e}")
            return

        # Make sure the directory path exists
        dir_path = os.path.join(os.getcwd(), *path_parts[:-1])
        os.makedirs(dir_path, exist_ok=True)

        # Create the filename
        save_path = os.path.join(dir_path, f"fuzzy_post_data_{filename}")

        try:
            with open(save_path, "wb") as f:
                f.write(post_data)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"[!] Failed to write POST data to file.\n")
            print(f"[!] Error writing to file '{save_path}': {e}")
            return

        self.send_response(200)
        self.end_headers()
        message = f"[+] POST data saved to: {save_path}\n"
        self.wfile.write(message.encode())
        print(message.strip())


parser = argparse.ArgumentParser(description="Fuzzy HTTP File Server")
parser.add_argument("-p", "--port", type=int, default=8000, help="Port to serve on (default: 8000)")
parser.add_argument("-d", "--directory", type=str, default=os.getcwd(), help="Directory to serve (default: current directory)")
args = parser.parse_args()

os.chdir(args.directory)

with socketserver.TCPServer(("", args.port), FuzzyHTTPRequestHandler) as httpd:
    print("\033[93mFound a bug or have a feature request? Reach out to @PakCyberbot (https://pakcyberbot.com)\033[0m")
    print(f"[+] Serving '{args.directory}' on port {args.port}")
    httpd.serve_forever()

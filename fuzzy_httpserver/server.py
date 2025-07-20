import http.server
import socketserver
import os
import argparse
from urllib.parse import unquote
import difflib
import hashlib
import re,subprocess

class FuzzyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def find_file_recursively(self, base_path, target_filename):
        """Recursively search for a file in all subdirectories"""
        target_lower = target_filename.lower()
        best_match = None
        best_score = 0
        best_path = None
        
        def calculate_score(query, candidate, is_file):
            query_lower = query.lower()
            candidate_lower = candidate.lower()
            
            # Base score from difflib
            base_score = difflib.SequenceMatcher(None, query_lower, candidate_lower).ratio()
            
            # Bonus for files
            file_bonus = 0.3 if is_file else 0
            
            # Bonus for exact extension match
            extension_bonus = 0
            if '.' in query and '.' in candidate:
                query_ext = query.split('.')[-1].lower()
                candidate_ext = candidate.split('.')[-1].lower()
                if query_ext == candidate_ext:
                    extension_bonus = 0.2
            
            # Bonus for prefix match
            prefix_bonus = 0
            if candidate_lower.startswith(query_lower):
                prefix_bonus = 0.1
            
            # Bonus for exact name match (case-insensitive)
            exact_bonus = 0
            if query_lower == candidate_lower:
                exact_bonus = 0.5
            
            return base_score + file_bonus + extension_bonus + prefix_bonus + exact_bonus
        
        for root, dirs, files in os.walk(base_path):
            # Check files in current directory
            for file in files:
                score = calculate_score(target_filename, file, True)
                if score > best_score and score >= 0.5:
                    best_score = score
                    best_match = file
                    best_path = root
        
        return best_match, best_path, best_score

    def smart_file_matcher(self, query, base_path, dir_preference=None):
        """Smart file matching with path analysis and keyword prioritization"""
        query_lower = query.lower()
        matching_files = []
        
        # Keywords for prioritization (higher index = higher priority)
        priority_keywords = ['64', 'x64', 'amd64', '32', 'x86', 'win32', 'win64']
        
        def calculate_path_score(file_path, query):
            """Calculate score based on path analysis and keywords"""
            score = 0
            path_lower = file_path.lower()
            query_lower = query.lower()
            
            # Base similarity score
            score += difflib.SequenceMatcher(None, query_lower, path_lower).ratio() * 0.3
            
            # File name matching (without extension)
            file_name = os.path.splitext(os.path.basename(file_path))[0].lower()
            if file_name == query_lower:
                score += 1.0  # Exact file name match
            
            # Extension matching
            if '.' in query and '.' in file_path:
                query_ext = query.split('.')[-1].lower()
                file_ext = file_path.split('.')[-1].lower()
                if query_ext == file_ext:
                    score += 0.3
            
            # Directory preference scoring
            if dir_preference:
                dir_pref_lower = dir_preference.lower()
                if dir_pref_lower in path_lower:
                    score += 1.5  # Heavy bonus for directory preference
                else:
                    score -= 0.5  # Penalty for non-preferred directory
            
            # Query keyword analysis - this is the most important part
            query_has_64 = '64' in query_lower
            query_has_32 = '32' in query_lower
            path_has_64 = any(kw in path_lower for kw in ['64', 'x64', 'amd64'])
            path_has_32 = any(kw in path_lower for kw in ['32', 'x86', 'win32'])
            
            # If query has 64, heavily prioritize 64-bit paths
            if query_has_64 and path_has_64:
                score += 2.0
            elif query_has_64 and path_has_32:
                score -= 1.0  # Penalize 32-bit when 64 is requested
            
            # If query has 32, heavily prioritize 32-bit paths
            if query_has_32 and path_has_32:
                score += 2.0
            elif query_has_32 and path_has_64:
                score -= 1.0  # Penalize 64-bit when 32 is requested
            
            # Default preference: 64-bit over 32-bit (when no specific preference)
            if not query_has_64 and not query_has_32:
                if path_has_64:
                    score += 0.5  # Bonus for 64-bit by default
                elif path_has_32:
                    score += 0.2  # Lower bonus for 32-bit
            
            # Path keyword analysis (secondary priority)
            for i, keyword in enumerate(priority_keywords):
                if keyword in path_lower:
                    # Higher priority for keywords that appear later in the list
                    keyword_score = (i + 1) / len(priority_keywords) * 0.2
                    score += keyword_score
            
            # Query keyword matching in path
            query_words = query_lower.split()
            for word in query_words:
                if word in path_lower:
                    score += 0.1
            
            # Character-by-character analysis
            char_matches = 0
            query_chars = set(query_lower.replace('.', ''))
            path_chars = set(path_lower.replace('.', '').replace('/', '').replace('\\', ''))
            if query_chars:
                char_matches = len(query_chars.intersection(path_chars)) / len(query_chars)
            score += char_matches * 0.1
            
            return score
        
        # Search recursively for files
        for root, dirs, files in os.walk(base_path):
            for file in files:
                # Check if file name (without extension) matches query
                file_name = os.path.splitext(file)[0].lower()
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, base_path).replace('\\', '/')
                
                # Check for exact file name match
                if file_name == query_lower:
                    score = calculate_path_score(rel_path, query)
                    matching_files.append((rel_path, score, file))
                # Check for partial matches - more flexible matching
                elif (file_name.startswith(query_lower) or  # file starts with query
                      query_lower.startswith(file_name) or  # query starts with file
                      query_lower in file_name or           # query is contained in file
                      file_name in query_lower):            # file is contained in query
                    score = calculate_path_score(rel_path, query)
                    if score >= 0.3:  # Lower threshold for partial matches
                        matching_files.append((rel_path, score, file))
        
        # Sort by score (highest first)
        matching_files.sort(key=lambda x: x[1], reverse=True)
        
        return matching_files

    def do_GET(self):
        requested = unquote(self.path.lstrip("/"))
        full_base = os.getcwd()
        path_parts = requested.split("/")
        base_path = full_base
        remaining_parts = path_parts.copy()

        # Step 1: Parse the URL to extract filename and filter chain
        filename = None
        filter_chain = []
        
        if len(path_parts) == 1:
            # Single part: /mimi
            filename = path_parts[0]
        elif len(path_parts) >= 2:
            # Multiple parts: /mimi/64/exe
            filename = path_parts[0]
            filter_chain = path_parts[1:]  # All parts after filename are filters

        try:
            entries = os.listdir(base_path)
        except Exception:
            entries = []

        # Separate files and directories
        files = []
        dirs = []
        for entry in entries:
            full_path = os.path.join(base_path, entry)
            if os.path.isfile(full_path):
                files.append(entry)
            else:
                dirs.append(entry)

        # Step 2: Use smart file matcher to find initial files
        matching_files = self.smart_file_matcher(filename, full_base)
        
        if matching_files:
            # Apply progressive filtering
            current_results = matching_files
            
            for filter_keyword in filter_chain:
                filtered_results = []
                filter_lower = filter_keyword.lower()
                
                for rel_path, score, file_name in current_results:
                    if filter_lower in rel_path.lower():
                        # Boost score for filter match
                        filtered_score = score + 1.0
                        filtered_results.append((rel_path, filtered_score, file_name))
                
                current_results = filtered_results
                
                # If no results after filtering, break
                if not current_results:
                    break
            
            # Use the final filtered results
            matching_files = current_results
            matching_files.sort(key=lambda x: x[1], reverse=True)
            
            # If multiple files found, show options
            if len(matching_files) > 1:
                self.send_response(300)  # Multiple choices
                self.send_header("Content-type", "text/plain")
                
                if filter_chain:
                    filter_str = "/".join(filter_chain)
                    self.send_header("Server-Reply", f"Multiple files found matching '{filename}' with filters '{filter_str}'. Choose one:")
                else:
                    self.send_header("Server-Reply", f"Multiple files found matching '{filename}'. Choose one:")
                self.end_headers()
                
                if filter_chain:
                    filter_str = "/".join(filter_chain)
                    print(f"\033[93m[?] Multiple files found matching '{filename}' with filters '{filter_str}':\033[0m")
                else:
                    print(f"\033[93m[?] Multiple files found matching '{filename}':\033[0m")
                for i, (rel_path, score, file_name) in enumerate(matching_files, 1):
                    full_path = f"/{rel_path}"
                    self.wfile.write(f"{i}. {full_path} (score: {score:.2f})\n".encode())
                    print(f"\033[94m  {i}. {full_path} (score: {score:.2f})\033[0m")
                
                print()  # Empty line for spacing
                return
            
            # If exactly one file found, serve it
            elif len(matching_files) == 1:
                rel_path, score, file_name = matching_files[0]
                self.path = f"/{rel_path}"
                if filter_chain:
                    filter_str = "/".join(filter_chain)
                    print(f"\033[94m[+] Smart matched '{filename}' with filters '{filter_str}' -> '{self.path}' (score: {score:.2f})\033[0m")
                else:
                    print(f"\033[94m[+] Smart matched '{filename}' -> '{self.path}' (score: {score:.2f})\033[0m")
                return super().do_GET()
            
            # If no files found after filtering
            elif len(matching_files) == 0:
                self.send_response(404)
                self.send_header("Content-type", "text/plain")
                if filter_chain:
                    filter_str = "/".join(filter_chain)
                    self.send_header("Server-Reply", f"No files found matching '{filename}' with filters '{filter_str}'.")
                else:
                    self.send_header("Server-Reply", f"No files found matching '{filename}'.")
                self.end_headers()
                if filter_chain:
                    filter_str = "/".join(filter_chain)
                    print(f"\033[91m[!] No files found matching '{filename}' with filters '{filter_str}'.\033[0m")
                else:
                    print(f"\033[91m[!] No files found matching '{filename}'.\033[0m")
                return

        # Step 3: Fallback to exact file match in current directory
        file_mapping = {f.lower(): f for f in files}
        if filename.lower() in file_mapping:
            self.path = "/" + file_mapping[filename.lower()]
            print(f"\033[94m[+] Exactly matched the file '{filename}' -> '{self.path}'\033[0m")
            return super().do_GET()

        # Step 4: Fallback to exact directory match
        dir_mapping = {d.lower(): d for d in dirs}
        if filename.lower() in dir_mapping:
            self.path = "/" + dir_mapping[filename.lower()]
            print(f"\033[94m[+] Exactly matched the directory '{filename}' -> '{self.path}'\033[0m")
            return super().do_GET()

        # Step 5: Fallback to fuzzy matching
        best_match = None
        best_score = 0
        best_type = None

        # Score function that prioritizes files and exact extensions
        def calculate_score(query, candidate, is_file):
            query_lower = query.lower()
            candidate_lower = candidate.lower()
            
            # Base score from difflib
            base_score = difflib.SequenceMatcher(None, query_lower, candidate_lower).ratio()
            
            # Bonus for files
            file_bonus = 0.3 if is_file else 0
            
            # Bonus for exact extension match
            extension_bonus = 0
            if '.' in query and '.' in candidate:
                query_ext = query.split('.')[-1].lower()
                candidate_ext = candidate.split('.')[-1].lower()
                if query_ext == candidate_ext:
                    extension_bonus = 0.2
            
            # Bonus for prefix match
            prefix_bonus = 0
            if candidate_lower.startswith(query_lower):
                prefix_bonus = 0.1
            
            # Bonus for exact name match (case-insensitive)
            exact_bonus = 0
            if query_lower == candidate_lower:
                exact_bonus = 0.5
            
            return base_score + file_bonus + extension_bonus + prefix_bonus + exact_bonus

        # Check files first (higher priority)
        for file in files:
            score = calculate_score(filename, file, True)
            if score > best_score and score >= 0.5:
                best_score = score
                best_match = file
                best_type = "file"

        # Then check directories (lower priority)
        for dir_name in dirs:
            score = calculate_score(filename, dir_name, False)
            if score > best_score and score >= 0.5:
                best_score = score
                best_match = dir_name
                best_type = "directory"

        if best_match:
            self.path = "/" + best_match
            type_str = "file" if best_type == "file" else "directory"
            print(f"\033[92m[+] Fuzzy matched '{filename}' -> '{self.path}' ({type_str}, score: {best_score:.2f})\033[0m")
            return super().do_GET()

        # Step 6: No match — 404 response and list files/dirs on server side
        self.send_response(404)
        self.send_header("Content-type", "text/plain")
        self.send_header("Server-Reply", "No file matched.")
        self.end_headers()
        print(f"\033[91m[!] No exact or fuzzy match for '{filename}'.\033[0m")

        print(f"\033[95m[>] Available entries in /:\033[0m\n")

        # Show files first, then directories
        for f in sorted(files):
            print(f"\033[93m/{f} (F)\033[0m")
        
        for f in sorted(dirs):
            print(f"\033[94m/{f} (D)\033[0m")

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

        # Compute MD5
        md5 = hashlib.md5(post_data).hexdigest()
        size_bytes = len(post_data)
        size_kb = size_bytes / 1024

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
        message = (
            f"\n\n"
            f"\033[30;107m[+] POST data saved to: {save_path}\033[0m\n"
            f"\033[30;107m[+] Size: {size_bytes} bytes ({size_kb:.2f} KB)\033[0m\n"
            f"\033[30;107m[+] MD5: {md5}\033[0m\n"
            f"\n\n"
        )
        self.wfile.write(message.encode())
        print(message.strip())

# Methods to get all network interfaces and their IPs to keep this module self-contained
def get_network_interfaces():
    """Get all network interfaces and their IP addresses using ifconfig"""
    interfaces = []
    
    try:
        result = subprocess.run(['ifconfig'], 
                              capture_output=True, text=True, check=True)
        interfaces = parse_ifconfig_output(result.stdout)
        
    except subprocess.CalledProcessError:
        print("Error: ifconfig command failed")
        return []
    except FileNotFoundError:
        print("Error: ifconfig command not found")
        return []
    except Exception as e:
        print(f"Error getting network interfaces: {e}")
        return []
    
    return interfaces

def parse_ifconfig_output(output):
    """Parse output from ifconfig command"""
    interfaces = []
    current_interface = None
    
    for line in output.split('\n'):
        if line and not line.startswith(' ') and not line.startswith('\t'):
            interface_match = re.match(r'^([^:\s]+)', line)
            if interface_match:
                current_interface = interface_match.group(1)
        
        elif current_interface and ('inet ' in line or 'inet addr:' in line):
            
            ip_match = re.search(r'inet\s+(?:addr:)?([0-9.]+)', line)
            if ip_match:
                ip_address = ip_match.group(1)
                interfaces.append((current_interface, ip_address))
    
    return interfaces

def list_all_interfaces():
    print("Network Interfaces and IP Addresses:")
    print("-" * 40)
    
    interfaces = get_network_interfaces()
    
    if not interfaces:
        print("No network interfaces found with IP addresses.")
        return
    
    # Display results in the requested format
    for interface_name, ip_address in interfaces:
        if 'tun' in interface_name or 'eth' in interface_name:
            print(f"\033[35m{interface_name}: {ip_address}\033[0m")

    print("-" * 40)


parser = argparse.ArgumentParser(description="Fuzzy HTTP File Server")
parser.add_argument("-p", "--port", type=int, default=8000, help="Port to serve on (default: 8000)")
parser.add_argument("-d", "--directory", type=str, default=os.getcwd(), help="Directory to serve (default: current directory)")
args = parser.parse_args()

os.chdir(args.directory)


with socketserver.TCPServer(("", args.port), FuzzyHTTPRequestHandler) as httpd:
    print(f"[+] Serving '{args.directory}' on port {args.port}")
    print()
    list_all_interfaces()
    print()
    httpd.serve_forever()


# 🔥 fuzzy-httpserver

A lightweight, zero-dependency Python HTTP file server with fuzzy filename matching and automatic fallback directory listing. Serve files easily without requiring users to know exact filenames — great for red teams, internal tooling, and lazy typing 😎.

---

## 🚀 Features

- 🔍 Fuzzy and prefix-based filename matching
- 🧾 Server-side logs directory contents if no file is matched
- ⚙️ Supports custom port and directory configuration
- ✅ No external dependencies — plug-and-play
- 🐍 Written in pure Python 3
- 📤 Supports POST data requests
- 🎨 Colored server-side output for better readability

---

## 📦 Installation

Install via pip:

```bash
pip install fuzzy-httpserver
````

---

## 🧪 Usage

Serve the current directory on the default port (8000):

```bash
fuzzy-httpserver
```

Serve a specific directory on a custom port:

```bash
fuzzy-httpserver -d /opt/tools -p 9001
```

### Example

```bash
wget http://<ip>:8000/ligolo-win
```

Even if the exact file is `ligolo-Agent-Windows-amd.exe`, it will still serve the file thanks to fuzzy matching. If nothing is found, you’ll get:

```
[!] File not found. Available files:

- chisel_windows
- payload_generator
```

Basically the list of files on that server directory

---

## 🛠 Command-Line Options

| Option              | Description                               |
| ------------------- | ----------------------------------------- |
| `-p`, `--port`      | Port to listen on (default: 8000)         |
| `-d`, `--directory` | Directory to serve (default: current dir) |

## 📨 POST Support

You can now send raw data via HTTP POST, and it will be saved on the server as a file. The filename will be prefixed with `fuzzy_post_data_` followed by the requested name.

### Example

```bash
curl --data @file.txt http://<ip>:8000/mydump.txt
#OR
curl --data "username=admin&password=1234" http://<ip>:8000/formdata.txt
```

---

## 🧠 Why?

Sometimes during internal testing, CTFs, or red teaming, we just want to serve files quickly — but can’t remember exact filenames. `fuzzy-httpserver` saves time by letting you guess loosely.

---

## 🧑‍💻 Author & Credits

Built with 💻 and ☕ by [PakCyberbot](https://pakcyberbot.com).

🔗 Connect with me:

* 🌐 Website: http://pakcyberbot.com
* Twitter/x: https://x.com/pakcyberbot
* GitHub: https://github.com/PakCyberbot
* LinkedIn: https://www.linkedin.com/in/pakcyberbot/
* Medium: https://medium.com/@pakcyberbot

---

## ✨ Contributions Welcome

Want to improve it? Found a bug? PRs and issues are welcome!

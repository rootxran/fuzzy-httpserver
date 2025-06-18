# 🔥 fuzzy-httpserver

A lightweight, zero-dependency Python HTTP file server with fuzzy filename matching and automatic fallback directory listing. Serve files easily without requiring users to know exact filenames — great for red teams, internal tooling, and lazy typing 😎.

---

## 🚀 Features

- 🔍 Fuzzy and prefix-based filename matching
- 📄 Shows available files when no match is found
- 🧾 Text-based fallback listing (CLI-friendly)
- ⚙️ Custom port and directory support
- ✅ No external dependencies
- 🐍 Pure Python 3

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

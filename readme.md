<div align="center">

# ✦ SMART SEARCH

### AI Spotlight for your computer.

Search images, videos, audio, and documents using natural language.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey)]()
[![Powered by](https://img.shields.io/badge/Powered%20by-Google%20Gemini-4285F4)]()

[Download](https://github.com/deepanmpc/SMART-SEARCH/releases) · [Website](https://deepanmpc.github.io/SMART-SEARCH) · [Documentation](docs/)

</div>

---

## ✨ What is Smart Search?

Smart Search is a **local, AI-powered search engine** that gives your computer a "semantic brain". Instead of hunting for filenames, just type what you remember:

> *"screenshot of the meeting notes about Q4 revenue"*
> *"photo of my dog at the park from last summer"*
> *"that PDF explaining transformer architectures"*
> *"audio recording from the team sync"*

It works across **images, videos, audio, PDFs, Word docs, and code files** using the power of Google Gemini Multimodal Embeddings.

---

## 🎬 Demo

![Smart Search Demo](https://raw.githubusercontent.com/deepanmpc/SMART-SEARCH/main/assets/demo.gif)

*Note: Replace with actual demo GIF once recorded.*

---

## 🚀 Key Features

- 🧠 **AI Semantic Search**: Search by meaning, not titles. "sunset at the beach" finds the right file even if it's named `IMG_9021.jpg`.
- 🎨 **Multimodal Support**: One search for everything. Images, videos, audio, and complex documents (PDF, DOCX).
- ⚡ **Blazing Fast**: Spotlight-style launcher opening in **<150ms**.
- 👁️ **Instant Preview**: Rich preview pane with thumbnails, text snippets, and metadata.
- 🤖 **AI Assistant Mode**: Ask questions about your files: `ask what do my meeting notes say about our launch date?`
- 🔒 **Privacy First**: Everything runs **100% locally**. Your files never leave your machine.
- 🖱️ **Keyboard-First**: Full navigation with arrows, `Space` to preview, and `Enter` to open.

---

## 🏗️ Architecture

```mermaid
graph TD
    A[User Files] --> B[Content Extraction]
    B --> C[Gemini API]
    C -->|768d Embeddings| D[FAISS Vector Index]
    D --> E[Semantic Search]
    F[User Query] --> G[Gemini API]
    G -->|Query Vector| E
    E --> H[Instant Results & Previews]
```

**Tech Stack:** Electron, FastAPI (Python), Google Gemini, FAISS, SQLite.

---

## ⌨️ Keyboard shortcuts

| Shortcut | Action |
|----------|--------|
| `⌘ Shift Space` | Open / Close Launcher |
| `↑ ↓` | Navigate results |
| `Space` | Preview result |
| `Enter` | Open file |
| `⌘ R` | Reveal in Finder / Explorer |
| `Esc` | Close launcher |

---

## 🔍 Example Queries

Try these in the search bar:
- `images from my trip to Goa`
- `notes about machine learning from last week`
- `screenshot where I was on a zoom call`
- `the PDF about neural network architectures`
- `video of the birthday party`
- `audio recording from the manager sync`

---

## 🔒 Privacy & Trust

Smart Search was built with privacy as a core principle:
- **No File Uploads**: Your actual files are never uploaded to any server.
- **Local Database**: The vector index (FAISS) and metadata (SQLite) are stored entirely on your computer.
- **API Security**: Only short text/image snippets are sent to Google Gemini to generate embeddings.

---

##  macOS Security Note

If you download the `.dmg` and see a message saying **"SMART SEARCH is damaged and can't be opened"**, this is a standard macOS security feature (Gatekeeper) for unsigned applications.

### 🛠️ How to fix:
1.  Open **Terminal** on your Mac.
2.  Run this command:
    ```bash
    sudo xattr -rd com.apple.quarantine /Applications/SMART\ SEARCH.app
    ```
3.  Enter your password and hit Enter.
4.  Open the app! It will work perfectly.

---

## 🛠️ Development

```bash
# Clone the repo
git clone https://github.com/deepanmpc/SMART-SEARCH.git
cd SMART-SEARCH

# Set up Python 3.11+ backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start the backend
python src/api.py

# In another terminal, start the Electron UI
cd launcher
npm install
npm start
```

---

## 👤 Creator

**Deepan Chandrasekaran** — AI Engineer building tools for intelligent computing.

- [GitHub](https://github.com/deepanmpc)
- [LinkedIn](https://linkedin.com/in/deepanmpc)

---

## 📄 License

MIT License. Free for everyone!

---

<div align="center">

**⭐ Star this repo if you find it useful!**

*"This is like Spotlight — but smarter."*

</div>

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

Smart Search is a **local, AI-powered search engine** for your computer. Instead of remembering filenames like `IMG_4821.jpg`, just type what you're looking for:

> *"photo of my dog at the park"*
> *"screenshot of the meeting notes"*
> *"Q4 revenue chart"*
> *"audio recording from last Tuesday"*

It works across **images, videos, audio, PDFs, Word docs, code files** — everything on your machine.

**Your files never leave your computer.** Only semantic embeddings are computed via the Gemini API.

---

## 🎬 Demo

<!-- Replace with actual demo GIF once recorded -->
<!-- ![Smart Search Demo](assets/demo.gif) -->

| Step | Action |
|------|--------|
| 1 | Press `⌘+Shift+Space` to open the launcher |
| 2 | Type a natural language query |
| 3 | Browse results with arrow keys, press `Space` to preview |
| 4 | Press `Enter` to open the file |

---

## 🚀 Features

| Feature | Description |
|---------|-------------|
| 🧠 **AI Semantic Search** | Search by meaning, not filenames. Powered by Gemini embeddings. |
| 🎨 **Multimodal** | Images, videos, audio, PDFs, DOCX, code — all in one place. |
| ⚡ **Real-Time Indexing** | New files become searchable within seconds. |
| 👁️ **Instant Preview** | See thumbnails, text snippets, and metadata before opening. |
| 🤖 **AI Ask Mode** | Ask questions about your files: `ask what do my notes say about transformers?` |
| 🔒 **Privacy First** | Everything runs locally. Files never leave your machine. |
| ⌨️ **Keyboard-First** | Spotlight-style UX with full keyboard navigation. |

---

## 📥 Download

| Platform | Download | Requirements |
|----------|----------|-------------|
| 🍎 macOS | [Smart Search.dmg](https://github.com/deepanmpc/SMART-SEARCH/releases/latest) | macOS 12+ |
| 🪟 Windows | [Smart Search Setup.exe](https://github.com/deepanmpc/SMART-SEARCH/releases/latest) | Windows 10+ |
| 🐧 Linux | [Smart Search.AppImage](https://github.com/deepanmpc/SMART-SEARCH/releases/latest) | Ubuntu 20.04+ |

### Quick Start
1. Download and install for your platform
2. Get a free [Gemini API key](https://aistudio.google.com/app/apikey)
3. Paste the key during first-launch setup
4. Choose a folder to index
5. Start searching!

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────┐
│   Electron UI   │────▷│  FastAPI Backend  │────▷│  Google Gemini│
│  (Launcher)     │◁────│  (Python)         │◁────│  (Embeddings) │
└─────────────────┘     └──────────────────┘     └───────────────┘
                              │       │
                        ┌─────┘       └─────┐
                        ▼                   ▼
                  ┌───────────┐      ┌───────────┐
                  │   FAISS   │      │  SQLite   │
                  │  (Vectors)│      │ (Metadata)│
                  └───────────┘      └───────────┘
```

**Pipeline:** Files → Content Extraction → Gemini Embeddings (768d) → FAISS Index → Semantic Search

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `⌘ Shift Space` | Open / close Smart Search |
| `↑ ↓` | Navigate results |
| `Enter` | Open selected file |
| `Space` | Preview file |
| `⌘ R` | Reveal in Finder |
| `Esc` | Close launcher |

---

## 🔍 Example Queries

```
images from my trip to Goa
notes about machine learning
screenshot where I was on a call
the PDF about neural network architectures
video of birthday party 2024
audio recording from meeting
```

---

## 📚 Documentation

- [Setup Guide](docs/setup.md) — Installation, API key, first index
- [Usage Guide](docs/usage.md) — Semantic search, filters, AI ask mode
- [FAQ](docs/faq.md) — Privacy, costs, supported file types

---

## 🛠️ Development

```bash
# Clone the repo
git clone https://github.com/deepanmpc/SMART-SEARCH.git
cd SMART-SEARCH

# Set up Python backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Add your API key
echo "GOOGLE_API_KEY=your_key_here" > src/.env

# Start the backend
python src/api.py

# In another terminal, start the Electron UI
cd launcher
npm install
npm start
```

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-thing`)
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

---

## 👤 Creator

**Deepan Chandrasekaran** — AI Engineer building tools for intelligent computing.

- [GitHub](https://github.com/deepanmpc)
- [LinkedIn](https://linkedin.com/in/deepanmpc)

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

<div align="center">

**⭐ Star this repo if you find it useful!**

*"This is like Spotlight — but smarter."*

</div>

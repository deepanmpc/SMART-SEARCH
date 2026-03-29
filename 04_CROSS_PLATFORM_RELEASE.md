# 04_CROSS_PLATFORM_RELEASE.md

SMART SEARCH --- Cross Platform App Release Guide

Author: Deepan Chandrasekaran

Goal: Release SMART SEARCH as a **fully open-source desktop
application** supporting:

-   macOS
-   Windows
-   Linux

The application will run locally and require the user to provide their
own Google AI Studio API key.

------------------------------------------------------------------------

# 1. Distribution Model

SMART SEARCH will be distributed as a **desktop application**.

Users download the installer from the project website.

Platforms:

macOS → .dmg\
Windows → .exe\
Linux → .AppImage

The app runs locally on the user's computer.

------------------------------------------------------------------------

# 2. Cross Platform Architecture

Final architecture:

Electron Launcher\
↓\
React UI\
↓\
Local Python Backend (FastAPI)\
↓\
FAISS + SQLite\
↓\
User File System

Electron communicates with the backend via HTTP API.

------------------------------------------------------------------------

# 3. Packaging Tools

Use:

electron-builder

Install:

npm install electron-builder --save-dev

Build command:

npm run build

------------------------------------------------------------------------

# 4. Build Targets

Configure electron-builder.

Example:

{ "mac": { "target": "dmg" }, "win": { "target": "nsis" }, "linux": {
"target": "AppImage" } }

Output folder:

dist/

------------------------------------------------------------------------

# 5. Python Backend Packaging

The Python backend must be bundled.

Two options:

Option A: Ship Python environment

Option B: Compile backend using PyInstaller.

Recommended:

pyinstaller src/api.py --onefile

This produces:

backend executable

Electron launches this process when app starts.

------------------------------------------------------------------------

# 6. Application Startup Flow

User opens SMART SEARCH.

Electron launcher starts.

Launcher checks:

1.  Backend running
2.  Config exists
3.  API key present

If backend not running:

start backend process

------------------------------------------------------------------------

# 7. Global Shortcut

Default shortcut:

CMD + SHIFT + SPACE

Linux / Windows:

CTRL + SHIFT + SPACE

This opens the floating search window.

------------------------------------------------------------------------

# 8. File System Permissions

macOS requires permission for:

Desktop\
Documents\
Downloads

The app must request permission before indexing.

------------------------------------------------------------------------

# 9. Local Data Storage

Store application data here:

macOS:

\~/Library/Application Support/SmartSearch

Windows:

AppData/Roaming/SmartSearch

Linux:

\~/.smartsearch

Stored data:

FAISS index\
SQLite metadata\
thumbnail cache\
user config

------------------------------------------------------------------------

# 10. Crash Logging

Add crash logging.

Logs location:

logs/

Log:

indexing errors\
API errors\
search failures

------------------------------------------------------------------------

# 11. Auto Updates (Optional)

If updates are needed later:

electron-updater

For open-source releases GitHub releases can host updates.

------------------------------------------------------------------------

# 12. Open Source Strategy

SMART SEARCH repository should include:

frontend/\
backend/\
launcher/\
docs/

Also include:

LICENSE (MIT recommended)

README.md

------------------------------------------------------------------------

# 13. Open Source Goal

SMART SEARCH should become:

AI-powered local search engine for any computer.

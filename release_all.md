# release_all.md

SMART SEARCH --- Full Automated Release Pipeline (Local → Binaries →
GitHub Release)

Author: Deepan Chandrasekaran

Goal: Create a **fully automated release pipeline** that allows you to:

1.  Build production installers locally
2.  Verify the app + API key onboarding flow
3.  Generate cross‑platform binaries (.dmg / .exe / .AppImage)
4.  Automatically publish them to GitHub Releases
5.  Make website download buttons trigger direct downloads

This guide assumes the SMART SEARCH app is already working locally.

------------------------------------------------------------------------

# OVERVIEW

Release process happens in **3 stages**:

Stage 1 --- Local Build & Verification\
Stage 2 --- Binary Packaging (Cross Platform)\
Stage 3 --- GitHub Automated Release Pipeline

------------------------------------------------------------------------

# STAGE 1 --- LOCAL BUILD & VERIFICATION

Before creating binaries ensure everything works locally.

Checklist:

• Electron launcher opens instantly\
• Python backend starts correctly\
• API key onboarding screen works\
• Folder indexing works\
• Search returns results\
• Preview system works\
• Keyboard shortcuts work

------------------------------------------------------------------------

## 1. Install Required Tools

Install dependencies:

    Node.js 18+
    Python 3.10+
    pip
    npm
    git

Install Electron dependencies:

    npm install

Install Python dependencies:

    pip install -r requirements.txt

------------------------------------------------------------------------

## 2. Verify API Key Setup Flow

The first launch should show:

Gemini API Key Screen

User flow:

1.  Click **Get API Key**
2.  Opens Google AI Studio
3.  User copies key
4.  Pastes key into input field
5.  Clicks **Save & Continue**
6.  Backend restarts automatically
7.  Indexing begins

------------------------------------------------------------------------

## 3. Local Run Command

Start the application locally:

    npm run dev

Expected behavior:

Launcher opens\
Setup wizard appears\
API key screen works\
Indexing works

------------------------------------------------------------------------

# STAGE 2 --- BINARY PACKAGING

Goal: Create installable binaries for:

macOS (.dmg)\
Windows (.exe)\
Linux (.AppImage)

------------------------------------------------------------------------

## 1. Install Build Tools

Install electron-builder:

    npm install electron-builder --save-dev

Install Python bundler:

    pip install pyinstaller

------------------------------------------------------------------------

## 2. Build Python Backend

Bundle the backend service:

    pyinstaller src/api.py --onefile --name smartsearch_backend

Output:

    dist/smartsearch_backend

Move this into:

    launcher/backend/

Electron will start this executable automatically.

------------------------------------------------------------------------

## 3. Configure electron-builder

Add to package.json:

    "build": {
      "appId": "ai.smartsearch.app",
      "productName": "SMART SEARCH",
      "mac": {
        "target": "dmg"
      },
      "win": {
        "target": "nsis"
      },
      "linux": {
        "target": "AppImage"
      }
    }

------------------------------------------------------------------------

## 4. Build Installers

Run:

    npm run build

Expected output folder:

    dist/

    SMARTSEARCH_mac.dmg
    SMARTSEARCH_windows.exe
    SMARTSEARCH_linux.AppImage

These are the **actual distributable installers**.

------------------------------------------------------------------------

# STAGE 3 --- GITHUB AUTOMATED RELEASE

Goal: Push a git tag → automatically build installers → publish GitHub
release.

------------------------------------------------------------------------

## 1. GitHub Actions Workflow

Create file:

    .github/workflows/release.yml

Example workflow:

    name: Build and Release

    on:
      push:
        tags:
          - "v*"

    jobs:
      build:
        runs-on: ubuntu-latest

        steps:
          - uses: actions/checkout@v3

          - name: Setup Node
            uses: actions/setup-node@v3
            with:
              node-version: 18

          - name: Install dependencies
            run: npm install

          - name: Build Electron App
            run: npm run build

          - name: Create Release
            uses: softprops/action-gh-release@v1
            with:
              files: |
                dist/*.dmg
                dist/*.exe
                dist/*.AppImage

------------------------------------------------------------------------

## 2. Create First Release

Run locally:

    git add -A
    git commit -m "Release v1.0.0"
    git tag v1.0.0
    git push origin main --tags

GitHub Actions will:

1.  Build binaries
2.  Create release
3.  Upload installers

------------------------------------------------------------------------

# DIRECT DOWNLOAD LINKS

Use these links in the website download buttons:

macOS:

    https://github.com/deepanmpc/SMART-SEARCH/releases/latest/download/SMARTSEARCH_mac.dmg

Windows:

    https://github.com/deepanmpc/SMART-SEARCH/releases/latest/download/SMARTSEARCH_windows.exe

Linux:

    https://github.com/deepanmpc/SMART-SEARCH/releases/latest/download/SMARTSEARCH_linux.AppImage

Users click → file downloads instantly.

------------------------------------------------------------------------

# OPTIONAL IMPROVEMENTS

Future upgrades:

• Apple notarization for macOS\
• Windows code signing\
• Auto updater for Electron\
• Crash analytics\
• Telemetry (optional)

------------------------------------------------------------------------

# FINAL RESULT

When finished:

User visits website\
Clicks download\
Installer downloads instantly

User installs app\
Launches SMART SEARCH

First launch:

API key setup screen appears

User pastes Gemini API key\
App restarts backend automatically

User indexes folder\
Search works instantly.

SMART SEARCH is now **fully distributable and production-ready**.

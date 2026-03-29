# 05_ONBOARDING_AND_USAGE.md

SMART SEARCH --- User Onboarding & Setup Guide

Author: Deepan Chandrasekaran

Goal: Make first-time user setup extremely simple.

The user should be able to start searching their files within **2
minutes**.

------------------------------------------------------------------------

# 1. First Launch Experience

When the user opens the app for the first time:

Show a clean welcome screen.

Example:

Welcome to SMART SEARCH

Search your entire computer using AI.

------------------------------------------------------------------------

# 2. API Key Setup

SMART SEARCH uses Google's embedding models.

Users must provide their own API key.

Steps shown in UI:

1.  Visit Google AI Studio
2.  Create API key
3.  Copy key
4.  Paste into SMART SEARCH

------------------------------------------------------------------------

# 3. API Key Instructions

Provide a button:

Get API Key

Which opens:

https://aistudio.google.com/

Explain:

Create an API key → copy → paste here.

------------------------------------------------------------------------

# 4. API Key Storage

The key should be stored locally.

Location:

config.json

Example:

{ "google_api_key": "USER_KEY" }

Never upload user keys anywhere.

------------------------------------------------------------------------

# 5. Folder Selection

Next step:

Select folders to index.

Recommended folders:

Documents\
Desktop\
Downloads\
Pictures

User chooses what to index.

------------------------------------------------------------------------

# 6. Indexing Screen

Display indexing progress.

Example:

Indexing files...

1200 / 6000

Allow cancel.

------------------------------------------------------------------------

# 7. Completion Screen

When indexing finishes show:

Indexing Complete

You can now search your files.

Shortcut:

CMD + SHIFT + SPACE

------------------------------------------------------------------------

# 8. Usage Basics

Explain core usage.

Search examples:

"machine learning notes"

"screenshot of meeting"

"image with dog"

------------------------------------------------------------------------

# 9. File Interaction

Users can:

Press ENTER → open file

Press SPACE → preview file

Use arrow keys → navigate results

ESC → close launcher

------------------------------------------------------------------------

# 10. Search Filters

Explain filters:

All files

Images

Videos

Audio

Documents

------------------------------------------------------------------------

# 11. AI Ask Mode

Users can ask:

"what pdfs talk about transformers"

"find notes about neural networks"

The system searches across indexed files.

------------------------------------------------------------------------

# 12. Tutorial Video

Add a short tutorial video.

Length:

60--90 seconds.

Show:

index folder

search examples

preview files

------------------------------------------------------------------------

# 13. Help Menu

Inside launcher add:

Help

This opens:

User guide

------------------------------------------------------------------------

# 14. Documentation

Include a docs folder.

docs/

setup.md\
usage.md\
faq.md

------------------------------------------------------------------------

# 15. Final Goal

SMART SEARCH should feel:

simple

fast

powerful

Users should think:

"This is like Spotlight but smarter."

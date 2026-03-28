# PRODUCT_FIXES.md

SMART SEARCH --- Product Improvements Before Launch

Author: Deepan Chandrasekaran

This document lists the **critical product fixes** required before
launching SMART SEARCH publicly.

These improvements focus on **UX, reliability, and perceived value**,
which matter more than raw engineering.

------------------------------------------------------------------------

# 1. Remove Developer Metadata From UI

Current UI shows internal data such as:

-   \[Image: tile_768_768\]
-   Raw filenames with timestamps
-   Internal identifiers

Users should **never see system metadata**.

Instead display:

Example:

🖼 Screenshot -- Feb 6\
Image • High Match

Implementation:

Convert internal metadata to user-friendly labels.

Example mapping:

image/png → Image\
video/mp4 → Video\
audio/wav → Audio\
application/pdf → PDF Document

------------------------------------------------------------------------

# 2. Replace Raw Similarity Scores

Showing:

44%\
37%\
36%

creates **low confidence perception**.

Users think the system is inaccurate.

Instead use semantic labels.

Example:

Best Match\
Strong Match\
Possible Match

------------------------------------------------------------------------

# 3. Improve Search Result Layout

Current layout wastes space.

Recommended layout:

Search bar\
↓\
Top Result Preview\
↓\
Result List

Why:

Users usually want the **first result instantly**.

------------------------------------------------------------------------

# 4. Optimize Launcher Speed

The launcher must feel **instant**.

Target:

\<150ms open time

Solutions:

-   preload Electron window
-   background daemon running
-   avoid cold Python start

------------------------------------------------------------------------

# 5. Reduce Memory Usage

Electron + Python + FAISS can consume large RAM.

Target:

\<400MB total usage

Optimization ideas:

-   lazy load previews
-   limit thumbnail resolution
-   reduce FAISS RAM overhead

------------------------------------------------------------------------

# 6. Improve Memory Meter

Current display:

1.97%

Users do not understand percentages.

Better display:

Memory Usage\
120 MB / 500 MB

Optional bar:

██████████░░░░░░░

------------------------------------------------------------------------

# 7. Improve Result Naming

Example today:

Screenshot 2026-02-06 at 3.43PM.png

Better:

Screenshot -- Feb 6

Clean filenames automatically.

------------------------------------------------------------------------

# 8. Keyboard Navigation

Required for productivity users.

Keys:

↑ ↓ navigate results\
Enter open file\
Space preview\
Esc close launcher

------------------------------------------------------------------------

# 9. Faster Preview Loading

Preview panel should load:

\<200ms

Techniques:

-   thumbnail caching
-   lazy image decoding
-   async loading

------------------------------------------------------------------------

# 10. Better Error Handling

If indexing fails:

Show friendly message:

Unable to index this file.\
Unsupported format.

Never show stack traces.

------------------------------------------------------------------------

# 11. Add First-Time Setup Wizard

When user installs app:

Guide them through:

1.  Choose folders to index\
2.  Explain AI search\
3.  Start indexing

This reduces confusion.

------------------------------------------------------------------------

# 12. Improve Search Suggestions

While typing:

machine learning notes

suggest:

PDF documents\
Images\
Videos\
Notes

------------------------------------------------------------------------

# 13. Add Drag-and-Drop Indexing

User should be able to drag folders into the launcher.

Flow:

drag folder → drop → start indexing

------------------------------------------------------------------------

# 14. Indexing Progress UI

During indexing show:

Indexing...\
1200 / 5000 files

Add cancel button.

------------------------------------------------------------------------

# 15. Visual Polish

Improve:

-   icons
-   spacing
-   animation
-   hover effects

Goal:

Match polish level of Raycast.

------------------------------------------------------------------------

# 16. Final Goal

Before launch the product should feel:

Fast\
Simple\
Magical\
Reliable

Engineering alone does not sell products.

User experience does.

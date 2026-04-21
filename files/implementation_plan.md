# Implementation Plan

## Phase 1: Code Consolidation
- Compare the top two latest files (`8.1_fixing the cookie thing` and `major UI3b`).
- Establish the definitively best file as `main.py`.
- Archive all other `.py` files into an `old_versions` folder to clean up the root directory.

## Phase 2: Resolving UI Freezes
- Refactor the `DownloadEngine` class.
- Instead of using `threading.Thread(target=ydl.download)`, we will spawn a separate `subprocess` that runs a lightweight Python wrapper or the `yt-dlp` CLI directly.
- Read from the subprocess `stdout`/`stderr` using an asynchronous thread to update the UI progress bars via the tkinter `Queue` system smoothly.

## Phase 3: Optimizing the `.exe` Build
- Revise `Vidra_downloader.spec`.
- Ensure `--onedir` is used for fastest load times (avoiding temp extraction overhead of `--onefile`).
- Strip out unused PyInstaller imports.
- Test the `.exe` to verify it launches instantly without lag and handles multi-concurrency without throwing memory/GIL bottlenecks.

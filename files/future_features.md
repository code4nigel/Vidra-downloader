# Future Features & Improvements

1. **Non-blocking Multi-threaded Architecture**
   - Rearchitect the download engine to use true non-blocking concurrency (e.g., separating workers into subprocesses).
   - This will allow users to queue up 5-10 videos at once without the UI hanging or the program crashing.

2. **Lag-Free Standalone Executable**
   - Optimize the PyInstaller `.spec` to use a fast-launching directory model instead of a compressed `--onefile` if that was the cause.
   - Use lazy loading for heavy libraries (only import `yt-dlp` or `customtkinter` right when needed) to drop startup times to under 1-2 seconds.
   - Profile the boot sequence to eliminate any unnecessary checks.

3. **Codebase Consolidation**
   - Move away from file-level backups (e.g., `Vidra_v2.py`, `Vidra_v3.py`). Delete or archive the old `.py` files and establish a single `main.py`.
   - Setup a clean `/src` folder structure separating UI elements, Download Logic, and Utilities.

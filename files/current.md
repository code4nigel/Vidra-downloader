# Current Status of Vidra Downloader

## Why so many `.py` files?
The project folder contains many Python files because iterative backups were created during the development process. Each time a major feature (like UI overhauls, Dev Mode, or fixing cookies) was implemented, a new copy of the script was saved instead of using Git version control for branching.

## Which file is the latest / working the best?
Based on the file modification dates and internal version numbers:
- `Vidra_downloader_8.1_fixing the cookie thing.py` (Version 2.7.3) and `Vidra_downloader_major UI3b trying to fix the devmode fetch thing and normal user 1080p quality thing.py` are the most recently updated and most feature-complete.
- The original `Vidra_downloader.py` file is currently stuck at an older version (v2.0.1) and lacks the newer UI components and bug fixes.
- **Next Step**: We need to determine exactly which of the top two is the true final version and rename it to `vidra_main.py` (or similar) to act as the single source of truth moving forward.

## Executable Lag Issue
The previous method of building the `.exe` (likely using PyInstaller with `--onefile` or heavily bundled directories) causes lag because compressing/extracting large libraries like `customtkinter`, `yt-dlp`, and `ffmpeg` takes a significant toll on system resources during startup. Furthermore, large dependency trees slow down module importing.

## Multi-threading and UI Freezes
Currently, the app uses standard `threading.Thread` with a `Queue` for `yt-dlp` operations. However, Python's Global Interpreter Lock (GIL) and heavy I/O operations from `yt-dlp` can still block the main process, resulting in UI hitches or "not responding" states. To fix this and support multiple concurrent downloads, `yt-dlp` operations should ideally be offloaded to isolated processes (e.g., using `multiprocessing` or `subprocess`), communicating via IPC or stdout.

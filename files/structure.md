# Vidra Downloader - Project Structure

## 📂 Project Root (`VidraProject6/`)
- **`vidra_main.py`**: The minimal entry-point for the application. Primarily handles the safe bootstrapping of packages (via pip) and launches the main application loop.
- **`vidra_config.json`**: (Auto-generated/Git-ignored) Stores user persistence like settings profiles, custom accent colors, and player preferences.
- **`cookies.txt`**: (User-provided/Git-ignored) Used by yt-dlp to bypass age restrictions and login barriers.
- **`dwn_history.json`**: (Auto-generated/Git-ignored) Persistent file storing download history states for the "Manage" tab.

## 📂 `src/` (Core Logic & Modules)
- **`config.py`**: Central repository for all system-wide variables, styling tuples (Light/Dark mode mapping), hardcoded dimensions, and required python module dependencies (`REQUIRED_MODULES`).
- **`engine.py`**: Encapsulates external command lines and download runners.
  - `DownloadEngine`: Thin wrapper over the `yt-dlp` `YoutubeDL` object to cleanly handle `get_info` extraction and execution.
  - `YdlLogger`: Custom logger subclass that routes stdout logging strings from `yt-dlp` threads directly into the GUI's `update_queue`.
  
## 📂 `src/ui/` (Graphical Interface)
- **`app.py`**: The heavy lifter of the codebase. Defines `VidraApp` which is the `customtkinter.CTk` root window.
  - Controls grid layout, resizable sidebars, Light/Dark mode reactive styling.
  - Manages the Thread Queue (`check_queue`) to safely parse outputs back to GUI widgets.
  - Implements smart clipboard polling (`check_clipboard`) to automatically highlight download links.
- **`components.py`**: Defines reusable graphical objects.
  - `DownloadCard`: The visually polished "One UI" style chip dynamically spawned whenever a download triggers, featuring status indicators, thumbnails, progress bars, and operational buttons (Play, Delete, Folder, Logs).

## 📂 `archive/`
- Contains legacy builds, monolithic Python files from earlier versions of development, and outdated installers. Used strictly for reference.

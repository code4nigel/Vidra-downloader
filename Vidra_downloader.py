import customtkinter as ctk
from PIL import Image # Only Image needed, ImageEnhance, ImageFilter not directly used in the current GUI logic
import yt_dlp
import pyperclip
import subprocess
import sys
import os
import ctypes
import re # Added for resolution parsing
from tkinter import filedialog, messagebox # Keep tkinter for file dialogs and message boxes
import json # Import the json module for saving/loading settings

# --- Dependency Management and Initial Checks ---
# List of required Python modules for the application
REQUIRED_MODULES = ["yt_dlp", "pyperclip", "customtkinter"]

def ensure_packages():
    """
    Ensures all required Python packages are installed.
    Prints installation messages and returns True if any package was installed/updated.
    """
    updated = False
    for module in REQUIRED_MODULES:
        try:
            __import__(module)
            print(f"{module} already installed.")
        except ImportError:
            print(f"Installing missing module: {module}")
            # Use subprocess to install the missing module via pip
            subprocess.check_call([sys.executable, "-m", "pip", "install", module])
            updated = True
    return updated

def auto_update_packages():
    """
    Prompts the user to update required packages and performs the update if confirmed.
    """
    # Using messagebox for GUI context
    response = messagebox.askyesno("Update Packages", "Do you want to update yt-dlp, pyperclip, and customtkinter to the latest version?")
    if response:
        try:
            messagebox.showinfo("Updating", "Updating packages... This may take a moment. The application might temporarily freeze.")
            # Perform the upgrade for all required modules
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade"] + REQUIRED_MODULES)
            messagebox.showinfo("Update Complete", "Packages updated to the latest version!\nPlease restart the application for changes to take effect.")
        except Exception as e:
            messagebox.showerror("Update Error", f"Failed to update packages: {e}")

def _get_ffmpeg_executable_path():
    """
    Determines the full path to the ffmpeg.exe based on execution mode.
    - If bundled with PyInstaller, use relative path.
    - Otherwise, return "ffmpeg" to fall back to system-installed ffmpeg.
    This function is for internal use when calling subprocess.run().
    """
    if getattr(sys, 'frozen', False):  # PyInstaller EXE
        base_path = sys._MEIPASS if hasattr(sys, "_MEIPASS") else os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    ffmpeg_exe_path = os.path.join(base_path, "ffmpeg", "bin", "ffmpeg.exe")

    if os.path.exists(ffmpeg_exe_path):
        return ffmpeg_exe_path
    return "ffmpeg"  # fallback to system PATH if bundled not found

def get_ffmpeg_dir_for_yt_dlp():
    """
    Determines the directory path containing ffmpeg for yt-dlp's ffmpeg_location option.
    Returns the directory path if bundled, or "ffmpeg" to signify system PATH lookup for yt-dlp.
    """
    if getattr(sys, 'frozen', False):  # PyInstaller EXE
        base_path = sys._MEIPASS if hasattr(sys, "_MEIPASS") else os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    ffmpeg_bin_dir = os.path.join(base_path, "ffmpeg", "bin")
    
    # Check if the ffmpeg.exe exists within this determined bin directory
    if os.path.exists(os.path.join(ffmpeg_bin_dir, "ffmpeg.exe")):
        return ffmpeg_bin_dir # Return the directory for yt-dlp
    return "ffmpeg"  # Fallback to system PATH for yt-dlp

def check_ffmpeg():
    """
    Checks if FFmpeg is installed and accessible for subprocess calls.
    It uses _get_ffmpeg_executable_path() to find the path to the ffmpeg executable.
    """
    ffmpeg_path_to_check = _get_ffmpeg_executable_path()
    try:
        subprocess.run([ffmpeg_path_to_check, "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        messagebox.showerror(
            "FFmpeg Not Found",
            "FFmpeg is required but was not found.\n"
            "Please make sure ffmpeg.exe is bundled in the 'ffmpeg/bin' folder or installed in your system PATH."
        )
        return False

# Define settings file path
SETTINGS_FILE = "vidra_settings.json"

# --- Custom Dialog for Cookie Input ---
class CookieInputDialog(ctk.CTkToplevel):
    def __init__(self, master, title, prompt):
        super().__init__(master)
        self.title(title)
        self.transient(master)  # Make it a transient window relative to master
        self.grab_set()         # Make it modal

        self.result = None

        self.label = ctk.CTkLabel(self, text=prompt, wraplength=400)
        self.label.pack(padx=20, pady=10)

        self.textbox = ctk.CTkTextbox(self, width=400, height=200)
        self.textbox.pack(padx=20, pady=5, fill="both", expand=True)

        self.ok_button = ctk.CTkButton(self, text="OK", command=self.on_ok)
        self.ok_button.pack(pady=10)

        self.bind("<Return>", lambda event: self.on_ok()) # Allow Enter key to submit
        self.protocol("WM_DELETE_WINDOW", self.on_closing) # Handle window close button

        # Center the dialog on the main window
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() // 2) - (self.winfo_width() // 2)
        y = master.winfo_y() + (master.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def on_ok(self):
        """Called when the OK button is pressed or Enter key is hit."""
        self.result = self.textbox.get("1.0", ctk.END).strip()
        self.destroy()

    def on_closing(self):
        """Called when the window close button is pressed."""
        self.result = None # Indicate that the user cancelled
        self.destroy()

    def get_input(self):
        """Waits for the dialog to close and returns the input."""
        self.master.wait_window(self)
        return self.result


# --- Main Application Class ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Define color palettes for dynamic theming
        self.theme_colors = {
            "Dark": {
                "sidebar_bg": "#2b2b2b",
                "main_container_bg": "#1a1a1a",
                "main_panel_bg": "#252525",
                "title_bar_bg": "#1e1e1e", # This will no longer be used for the main title bar but kept in case other elements might reference it
                "entry_bg": "#333333",
                "option_menu_bg": "#333333",
                "button_fg": "#333333",
                "button_hover": "#444444",
                "red_button_fg": "#FF4136",
                "red_button_hover": "#E03B2F",
                "accent_green": "#00FFAA",
                "accent_red": "#FF4136",
                "gray_text": "gray",
                "label_text": "white" 
            },
            "Light": {
                "sidebar_bg": "#ededed",
                "main_container_bg": "#f5f5f5",
                "main_panel_bg": "#ffffff",
                "title_bar_bg": "#e0e0e0", # This will no longer be used for the main title bar but kept in case other elements might reference it
                "entry_bg": "#e5e5e5",
                "option_menu_bg": "#e5e5e5",
                "button_fg": "#d0d0d0",
                "button_hover": "#c0c0c0",
                "red_button_fg": "#CC332A", 
                "red_button_hover": "#A02820", 
                "accent_green": "#008855", 
                "accent_red": "#CC332A", 
                "gray_text": "#555555", 
                "label_text": "black" 
            }
        }
        
        # Load theme and cookie path settings or default
        self.settings = self.load_settings()
        # Initialize cookie_path here, but setup_cookie_path will finalize it
        self.cookie_path = os.path.abspath('cookies.txt') 
        self.current_mode = self.settings.get('theme', ctk.get_appearance_mode())
        ctk.set_appearance_mode(self.current_mode)
        self.current_colors = self.theme_colors[self.current_mode]


        # --- Initial Application Setup ---
        # Perform initial dependency and FFmpeg checks before setting up the GUI
        self.perform_initial_checks()

        # --- Window Setup (CustomTkinter) ---
        self.title("Vidra Downloader")
        self.geometry("1000x700")
        self.resizable(True, True)

        # Set custom window icon
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(script_dir, "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except ctk.Master.TclError as e:
                messagebox.showwarning("Icon Error", f"Could not set custom icon. Make sure 'icon.ico' is a valid .ico file.\nError: {e}")
        else:
            messagebox.showwarning("Icon Warning", "icon.ico not found in the script directory. Using default icon.")


        # Reverted overrideredirect settings to show default title bar and allow proper minimization
        self.overrideredirect(False) # Set to False to show default title bar
        # self.attributes("-transparentcolor", "#000001") # Not needed if overrideredirect is False
        # self.configure(fg_color="#000001") # Not needed if overrideredirect is False

        # Configure grid for main layout: sidebar (col 0) and main content (col 1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0) # Sidebar column, fixed width
        self.grid_columnconfigure(1, weight=1) # Main content column, expands

        # --- Sidebar Frame (Left Column) ---
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=self.current_colors["sidebar_bg"])
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1) # Row 4 pushes content to the top within sidebar

        # Sidebar 'Vidra' logo label
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Vidra", font=ctk.CTkFont(size=24, weight="bold"), text_color=self.current_colors["label_text"])
        self.logo_label.grid(row=0, column=0, padx=20, pady=20)

        # Sidebar 'Downloader' button (placeholder for navigation, currently doesn't change view)
        self.sidebar_downloader_button = ctk.CTkButton(self.sidebar_frame, text="\u2B07 Downloader", font=ctk.CTkFont(size=14), fg_color="transparent", hover_color=self.current_colors["button_hover"], anchor="w", text_color=self.current_colors["label_text"])
        self.sidebar_downloader_button.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        # Sidebar 'Update' button, connected to the updater function
        self.sidebar_update_button = ctk.CTkButton(self.sidebar_frame, text="🔄 Update", font=ctk.CTkFont(size=14), fg_color="transparent", hover_color=self.current_colors["button_hover"], anchor="w", command=auto_update_packages, text_color=self.current_colors["label_text"])
        self.sidebar_update_button.grid(row=2, column=0, padx=20, pady=5, sticky="ew")

        # Sidebar 'Theme' button, connected to theme toggling
        self.sidebar_theme_button = ctk.CTkButton(self.sidebar_frame, text="⚙️ Theme", font=ctk.CTkFont(size=14), fg_color="transparent", hover_color=self.current_colors["button_hover"], anchor="w", command=self.toggle_customtkinter_theme, text_color=self.current_colors["label_text"])
        self.sidebar_theme_button.grid(row=3, column=0, padx=20, pady=10, sticky="sw")

        # Sidebar 'Exit' button to close the application
        self.sidebar_exit_button = ctk.CTkButton(self.sidebar_frame, text="❌ Exit", font=ctk.CTkFont(size=14), fg_color="transparent", hover_color=self.current_colors["button_hover"], anchor="w", command=self.quit, text_color=self.current_colors["label_text"])
        self.sidebar_exit_button.grid(row=5, column=0, padx=20, pady=(0, 20), sticky="sw")

        # Bind mouse events to sidebar and logo for draggable window functionality
        # These bindings will still allow dragging from the sidebar, but the native title bar will also be draggable.
        self.sidebar_frame.bind("<ButtonPress-1>", self.start_drag)
        self.sidebar_frame.bind("<B1-Motion>", self.do_drag)
        self.logo_label.bind("<ButtonPress-1>", self.start_drag)
        self.logo_label.bind("<B1-Motion>", self.do_drag)

        # --- Main Area Container (Right Column) ---
        self.main_area_container = ctk.CTkFrame(self, corner_radius=0, fg_color=self.current_colors["main_container_bg"])
        self.main_area_container.grid(row=0, column=1, sticky="nsew")
        self.main_area_container.grid_rowconfigure(0, weight=1)
        self.main_area_container.grid_columnconfigure(0, weight=1)

        # --- Main Content Panel (Rounded visible content area) ---
        self.main_content_panel = ctk.CTkFrame(self.main_area_container, corner_radius=50, fg_color=self.current_colors["main_panel_bg"])
        self.main_content_panel.place(relx=0, rely=0, relwidth=1.0, relheight=1.0)
        self.main_content_panel.grid_columnconfigure(0, weight=1)

        # --- Custom Title Bar for Dragging and Window Controls (REMOVED) ---
        # The custom title bar frame and its buttons are removed to avoid duplication with native title bar.
        # self.title_bar = ctk.CTkFrame(self.main_content_panel, fg_color=self.current_colors["title_bar_bg"], corner_radius=0)
        # self.title_bar.pack(fill="x", pady=0, ipady=5)
        # self.title_label_bar = ctk.CTkLabel(self.title_bar, text="Vidra", font=ctk.CTkFont(size=16, weight="bold"), text_color=self.current_colors["label_text"])
        # self.title_label_bar.pack(side="left", padx=10, pady=5)
        # self.close_button = ctk.CTkButton(self.title_bar, text="X", width=30, height=20, corner_radius=5, fg_color=self.current_colors["red_button_fg"], hover_color=self.current_colors["red_button_hover"], command=self.quit, text_color=self.current_colors["label_text"])
        # self.close_button.pack(side="right", padx=10, pady=5)
        # self.minimize_button = ctk.CTkButton(self.title_bar, text="_", width=30, height=20, corner_radius=5, fg_color=self.current_colors["button_fg"], hover_color=self.current_colors["button_hover"], command=lambda: self.iconify(), text_color=self.current_colors["label_text"])
        # self.minimize_button.pack(side="right", padx=5, pady=5)
        # self.title_bar.bind("<ButtonPress-1>", self.start_drag)
        # self.title_bar.bind("<B1-Motion>", self.do_drag)
        # self.title_label_bar.bind("<ButtonPress-1>", self.start_drag)
        # self.title_label_bar.bind("<B1-Motion>", self.do_drag)

        # --- UI Widgets for Downloader Functionality ---

        header_top_content_frame = ctk.CTkFrame(self.main_content_panel, fg_color="transparent")
        header_top_content_frame.pack(fill="x", pady=(20, 0), padx=30)
        self.header_title = ctk.CTkLabel(header_top_content_frame, text="Vidra", font=ctk.CTkFont(size=32, weight="bold"), text_color=self.current_colors["label_text"])
        self.header_title.pack(side="right")

        # URL Entry and Paste button
        url_frame = ctk.CTkFrame(self.main_content_panel, fg_color="transparent")
        url_frame.pack(fill="x", padx=30, pady=(30, 5))
        self.url_entry = ctk.CTkEntry(url_frame, placeholder_text="Enter YouTube URL...", height=40, corner_radius=20, border_width=0, fg_color=self.current_colors["entry_bg"])
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.paste_button = ctk.CTkButton(url_frame, text="Paste", width=80, height=40, corner_radius=20, border_width=0, fg_color=self.current_colors["button_fg"], hover_color=self.current_colors["button_hover"], command=self.paste_clipboard, text_color=self.current_colors["label_text"])
        self.paste_button.pack(side="left")

        # Selected Quality/Resolution Display
        resolution_display_frame = ctk.CTkFrame(self.main_content_panel, fg_color="transparent")
        resolution_display_frame.pack(anchor="w", padx=30, pady=(20, 5))
        # Updated this label to explicitly set text_color
        self.selected_quality_label = ctk.CTkLabel(resolution_display_frame, text="Selected Quality:", font=ctk.CTkFont(size=16, weight="bold"), text_color=self.current_colors["label_text"])
        self.selected_quality_label.pack(side="left", padx=(0,10))
        self.resolution_label = ctk.CTkLabel(resolution_display_frame, text="N/A", font=ctk.CTkFont(size=36, weight="bold"), text_color=self.current_colors["accent_red"])
        self.resolution_label.pack(side="left")

        # Download Type Radio Buttons
        type_frame = ctk.CTkFrame(self.main_content_panel, fg_color="transparent")
        type_frame.pack(pady=20, padx=30, anchor="w")
        # Made these into instance variables for theme update
        self.type_label = ctk.CTkLabel(type_frame, text="Type:", font=ctk.CTkFont(size=14), text_color=self.current_colors["label_text"])
        self.type_label.pack(side="left", padx=(0, 10))
        self.type_var = ctk.StringVar(value="both") # Default to "both"
        self.radio_audio = ctk.CTkRadioButton(type_frame, text="Audio", variable=self.type_var, value="audio", command=self.update_size, text_color=self.current_colors["label_text"])
        self.radio_video = ctk.CTkRadioButton(type_frame, text="Video", variable=self.type_var, value="video", command=self.update_size, text_color=self.current_colors["label_text"])
        self.radio_both = ctk.CTkRadioButton(type_frame, text="Both", variable=self.type_var, value="both", command=self.update_size, text_color=self.current_colors["label_text"])
        self.radio_audio.pack(side="left", padx=5)
        self.radio_video.pack(side="left", padx=5)
        self.radio_both.pack(side="left", padx=5)

        # Button to fetch available formats from the URL
        self.fetch_formats_button = ctk.CTkButton(self.main_content_panel, text="Fetch Available Formats", fg_color=self.current_colors["button_fg"], hover_color=self.current_colors["button_hover"], command=self.fetch_formats_wrapper, text_color=self.current_colors["label_text"])
        self.fetch_formats_button.pack(pady=8)

        # Format selection dropdowns (video, audio, convert to)
        format_frame = ctk.CTkFrame(self.main_content_panel, fg_color="transparent")
        format_frame.pack(fill="x", padx=30, pady=10)

        self.video_formats = [] # To store fetched video formats
        self.audio_formats = [] # To store fetched audio formats

        self.video_var = ctk.StringVar(value="bv") # Variable for selected video format
        self.video_format_menu = ctk.CTkOptionMenu(format_frame, values=["- Video Quality -"], height=35, corner_radius=15, fg_color=self.current_colors["option_menu_bg"], command=self.video_var.set, text_color=self.current_colors["label_text"])
        self.video_format_menu.pack(side="left", fill="x", expand=True, padx=(0, 5))
        # Populate with default options initially
        self.populate_menu(self.video_format_menu, self.video_var, self.video_formats, self.get_default_video_formats())
        self.video_var.trace_add("write", self.update_resolution_label) # Update resolution label when video format changes
        self.video_var.trace_add("write", self.update_size) # Add trace for size update

        self.audio_var = ctk.StringVar(value="ba") # Variable for selected audio format
        self.audio_format_menu = ctk.CTkOptionMenu(format_frame, values=["- Audio Quality -"], height=35, corner_radius=15, fg_color=self.current_colors["option_menu_bg"], command=self.audio_var.set, text_color=self.current_colors["label_text"])
        self.audio_format_menu.pack(side="left", fill="x", expand=True, padx=5)
        # Populate with default options initially
        self.populate_menu(self.audio_format_menu, self.audio_var, self.audio_formats, self.audio_formats if self.audio_formats else self.get_default_audio_formats())
        self.audio_var.trace_add("write", self.update_resolution_label) # Trigger update for audio formats too
        self.audio_var.trace_add("write", self.update_size) # Add trace for size update


        self.convert_var = ctk.StringVar(value="") # Variable for conversion format
        convert_options = ["- Convert To -", "mp4", "mkv", "mov", "mp3", "wav", "aac"]
        self.convert_menu = ctk.CTkOptionMenu(format_frame, values=convert_options, height=35, corner_radius=15, fg_color=self.current_colors["option_menu_bg"], variable=self.convert_var, text_color=self.current_colors["label_text"])
        self.convert_menu.pack(side="left", fill="x", expand=True, padx=(5, 0))

        # Label to indicate if formats haven't been fetched yet
        self.not_fetched_label = ctk.CTkLabel(self.main_content_panel, text="(Using default 'best' quality — fetch formats to see more options)", text_color=self.current_colors["gray_text"])
        self.not_fetched_label.pack()

        # Label to display estimated download size
        self.size_label = ctk.CTkLabel(self.main_content_panel, text="Estimated total size: ?")
        self.size_label.pack(pady=5)

        # Filename entry field
        filename_frame = ctk.CTkFrame(self.main_content_panel, fg_color="transparent")
        filename_frame.pack(fill="x", padx=30, pady=10)
        filename_label = ctk.CTkLabel(filename_frame, text="Save As:", font=ctk.CTkFont(size=14), text_color=self.current_colors["label_text"])
        filename_label.pack(side="left", padx=(0, 10))
        self.filename_entry = ctk.CTkEntry(filename_frame, placeholder_text="My Video Title", height=35, corner_radius=17, border_width=0, fg_color=self.current_colors["entry_bg"])
        self.filename_entry.pack(fill="x", expand=True)

        # Main Download Button
        self.download_button = ctk.CTkButton(
            self.main_content_panel,
            text="DOWNLOAD",
            font=ctk.CTkFont(size=18, weight="bold"),
            height=50,
            corner_radius=25,
            border_width=0,
            fg_color=self.current_colors["red_button_fg"],
            hover_color=self.current_colors["red_button_hover"],
            command=self.download, # Connect to the download method
            text_color="white" # Force this text to be white
        )
        self.download_button.pack(fill="x", padx=30, pady=(20, 10))

        # Progress bar for download status
        self.progress_bar = ctk.CTkProgressBar(self.main_content_panel, orientation="horizontal", height=10, corner_radius=5)
        self.progress_bar.pack(fill="x", padx=30, pady=(0,10))
        self.progress_bar.set(0) # Initialize to 0%

        # Status label to show current operation
        self.status_label = ctk.CTkLabel(self.main_content_panel, text="Ready", font=ctk.CTkFont(size=12), text_color=self.current_colors["label_text"])
        self.status_label.pack(pady=(0,10))


        # Initial updates for size and resolution display
        self.update_size()
        self.update_resolution_label()
        self.current_video_title = None # Initialize to store the fetched video title

        # Apply the initial theme settings to all widgets after they are created
        self.apply_theme_to_widgets()
        # Initialize cookie path after widgets are setup and theme applied
        self.cookie_path = self.setup_cookie_path()


    def apply_theme_to_widgets(self):
        """Applies the current theme colors to all relevant widgets."""
        # Update custom background colors for frames
        self.sidebar_frame.configure(fg_color=self.current_colors["sidebar_bg"])
        self.main_area_container.configure(fg_color=self.current_colors["main_container_bg"])
        self.main_content_panel.configure(fg_color=self.current_colors["main_panel_bg"])
        # self.title_bar.configure(fg_color=self.current_colors["title_bar_bg"]) # Removed as title_bar frame is removed

        # Update button colors (background and hover)
        self.sidebar_downloader_button.configure(hover_color=self.current_colors["button_hover"])
        self.sidebar_update_button.configure(hover_color=self.current_colors["button_hover"])
        self.sidebar_theme_button.configure(hover_color=self.current_colors["button_hover"])
        self.sidebar_exit_button.configure(hover_color=self.current_colors["button_hover"])

        # self.close_button.configure(fg_color=self.current_colors["red_button_fg"], hover_color=self.current_colors["red_button_hover"]) # Removed
        # self.minimize_button.configure(fg_color=self.current_colors["button_fg"], hover_color=self.current_colors["button_hover"]) # Removed

        self.paste_button.configure(fg_color=self.current_colors["button_fg"], hover_color=self.current_colors["button_hover"])
        self.fetch_formats_button.configure(fg_color=self.current_colors["button_fg"], hover_color=self.current_colors["button_hover"])
        self.download_button.configure(fg_color=self.current_colors["red_button_fg"], hover_color=self.current_colors["red_button_hover"])

        # Update text colors for buttons and option menus
        self.sidebar_downloader_button.configure(text_color=self.current_colors["label_text"])
        self.sidebar_update_button.configure(text_color=self.current_colors["label_text"])
        self.sidebar_theme_button.configure(text_color=self.current_colors["label_text"])
        self.sidebar_exit_button.configure(text_color=self.current_colors["label_text"])

        # self.close_button.configure(text_color=self.current_colors["label_text"]) # Removed
        # self.minimize_button.configure(text_color=self.current_colors["label_text"]) # Removed

        self.paste_button.configure(text_color=self.current_colors["label_text"])
        self.fetch_formats_button.configure(text_color=self.current_colors["label_text"])
        self.download_button.configure(text_color="white") # Keep this text white regardless of theme

        # Update entry and option menu colors
        self.url_entry.configure(fg_color=self.current_colors["entry_bg"])
        self.video_format_menu.configure(fg_color=self.current_colors["option_menu_bg"], text_color=self.current_colors["label_text"])
        self.audio_format_menu.configure(fg_color=self.current_colors["option_menu_bg"], text_color=self.current_colors["label_text"])
        self.convert_menu.configure(fg_color=self.current_colors["option_menu_bg"], text_color=self.current_colors["label_text"])
        self.filename_entry.configure(fg_color=self.current_colors["entry_bg"])

        # Update specific label text colors
        self.logo_label.configure(text_color=self.current_colors["label_text"])
        # self.title_label_bar.configure(text_color=self.current_colors["label_text"]) # Removed
        self.header_title.configure(text_color=self.current_colors["label_text"])
        self.selected_quality_label.configure(text_color=self.current_colors["label_text"]) # Ensure this label changes color
        self.resolution_label.configure(text_color=self.current_colors["accent_red"])
        self.not_fetched_label.configure(text_color=self.current_colors["gray_text"])
        self.size_label.configure(text_color=self.current_colors["label_text"]) # Main color for size label, accent will override when calculated
        self.status_label.configure(text_color=self.current_colors["label_text"])
        
        # --- FIX: Update text colors for Type label and radio buttons ---
        self.type_label.configure(text_color=self.current_colors["label_text"])
        self.radio_audio.configure(text_color=self.current_colors["label_text"])
        self.radio_video.configure(text_color=self.current_colors["label_text"])
        self.radio_both.configure(text_color=self.current_colors["label_text"])
        # --- END FIX ---

        # Ensure update_size is called to refresh size_label's color, which uses themed text_color.
        self.update_size() # Recalculate and update the size label, which uses themed text_color.

    # --- Methods for Dependency and Environment Checks ---
    def perform_initial_checks(self):
        """
        Performs essential checks like Python version, package installation, and FFmpeg presence
        before the main GUI is fully displayed. Exits the application if critical issues are found.
        """
        if sys.version_info < (3, 8):
            messagebox.showerror("Python Version Error", "Python 3.8 or higher is required to run this application.")
            sys.exit(1) # Exit if Python version is too old

        if ensure_packages():
            messagebox.showinfo("Packages Installed", "All required packages are now installed. Please re-launch the application if prompted.")
            # Depending on if a new package was just installed, sometimes a restart is cleaner.
            # For simplicity, we just proceed, but in a robust app, you might suggest or force a restart here.

        # Check FFmpeg; if not found, the app cannot function for video/audio processing.
        if not check_ffmpeg():
            sys.exit(1) # Exit if FFmpeg is not found

    # --- GUI Theming and Utility Methods ---
    def load_settings(self):
        """Loads all saved settings from a JSON file."""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, KeyError):
                print(f"Warning: Could not read settings from {SETTINGS_FILE}. Using defaults.")
        return {} # Return empty dict if no settings file or error

    def save_settings(self):
        """Saves current settings (theme and cookie path) to a JSON file."""
        settings_to_save = {
            'theme': self.current_mode,
            'cookie_file_path': self.cookie_path # Save the potentially updated cookie path
        }
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(settings_to_save, f, indent=4) # Use indent for readability
        except IOError as e:
            print(f"Error: Could not save settings to {SETTINGS_FILE}: {e}")

    def toggle_customtkinter_theme(self):
        """Toggles between 'Dark' and 'Light' appearance modes for customtkinter and updates custom colors."""
        self.current_mode = "Dark" if self.current_mode == "Light" else "Light"
        ctk.set_appearance_mode(self.current_mode)
        self.current_colors = self.theme_colors[self.current_mode]
        self.apply_theme_to_widgets() # Apply new theme to all widgets
        self.save_settings() # Save all settings (theme and cookie path)
        self.status_label.configure(text=f"Theme set to {self.current_mode}")


    def simple_input(self, prompt):
        """
        Provides a simple input dialog to get string input from the user.
        Uses tkinter's simpledialog for simplicity, but could be replaced with a custom CTkDialog.
        """
        from tkinter import simpledialog
        return simpledialog.askstring("Input Required", prompt, parent=self)

    # --- Methods for Format Selection and Customization ---
    def customize_format(self, format_template):
        """
        Allows users to customize format templates (e.g., specifying max height, extension, or size).
        """
        if "{height}" in format_template:
            val = self.simple_input("Enter max resolution (e.g., 720):")
            if val and val.isdigit():
                return format_template.replace("{height}", val)
        elif "{ext}" in format_template:
            val = self.simple_input("Enter desired extension (e.g., mp4, webm, m4a):")
            if val:
                return format_template.replace("{ext}", val)
        elif "{size}" in format_template:
            val = self.simple_input("Enter max size in MB (e.g., 50):")
            if val and val.isdigit():
                return format_template.replace("{size}", f"{val}M")
        return format_template

    def populate_menu(self, menu_widget, var, options_list, formats_list_with_templates):
        """
        Populates a CTkOptionMenu with format options.
        `options_list` is the list of (format_id, label, filesize, *extra_info).
        `formats_list_with_templates` is used for default/fallback options that might require customization.
        """
        menu_widget.set(formats_list_with_templates[0][1] if formats_list_with_templates else "No Formats Found")
        actual_options = []
        option_to_template = {}

        # Build list of labels for display and map them back to their format IDs/templates
        for fid_template, label, _, *rest in formats_list_with_templates: # Unpack to capture extra info
            actual_options.append(label)
            option_to_template[label] = fid_template

        menu_widget.configure(values=actual_options)

        def on_option_select(selected_label):
            """Callback for when an option is selected from the menu."""
            template_to_use = option_to_template.get(selected_label, selected_label) # Use get for safety
            final_format = self.customize_format(template_to_use)
            var.set(final_format) # Set the underlying StringVar to the actual format ID/template
            # The trace_add on var will call update_size and update_resolution_label
            # self.update_size() # No need to call explicitly, trace will handle
            # self.update_resolution_label() # No need to call explicitly, trace will handle

        menu_widget.configure(command=on_option_select)
        if formats_list_with_templates:
            # Set the internal variable to the actual template initially
            var.set(formats_list_with_templates[0][0])
        else:
            var.set("") # Clear if no formats

    def get_default_video_formats(self):
        """Returns a list of default video format templates."""
        # Added height=0 and ext="" placeholders for consistency with fetched formats
        return [
            ("bv", "Best video (bv)", 0, 0, ""),
            ("bestvideo[ext={ext}]", "Best video-only with specific extension...", 0, 0, "{ext}"),
            ("bestvideo[height<={height}]", "Best video-only up to height...", 0, "{height}", ""),
            ("best[filesize<{size}]", "Best format under size...", 0, 0, ""),
        ]

    def get_default_audio_formats(self):
        """Returns a list of default audio format templates."""
        # Added abr=0 and ext="" placeholders for consistency with fetched formats
        return [
            ("ba", "Best audio (ba)", 0, 0, ""),
            ("bestaudio[ext={ext}]", "Best audio with specific extension...", 0, 0, "{ext}"),
            ("bestaudio", "Best audio (full)", 0, 0, ""),
        ]

    def get_resolution_value(self, label):
        """Helper to extract integer resolution from a format label (e.g., "1080p" -> 1080)."""
        try:
            if 'p' in label:
                return int(label.split('p')[0])
            return 0
        except ValueError:
            return 0

    def update_resolution_label(self, *args):
        """Updates the displayed resolution label based on selected video or audio format."""
        download_type = self.type_var.get()
        display_text = "N/A" # Default text

        if download_type == "video" or download_type == "both":
            selected_fid_or_template = self.video_var.get()
            # Try to find the format in the fetched list first
            found_format = next((f for f in self.video_formats if f[0] == selected_fid_or_template), None)
            
            if found_format:
                height = found_format[3] # height is 4th element (index 3)
                ext = found_format[4] # ext is 5th element (index 4)
                if height and height != 0:
                    display_text = f"{height}p"
                elif ext:
                    display_text = f"Video ({ext.upper()})"
                else:
                    display_text = "Video (Details TBA)"
            # Handle default templates
            elif selected_fid_or_template == "bv":
                display_text = "Best Video"
            elif "{height}" in selected_fid_or_template:
                display_text = "Custom Height Video"
            elif "{ext}" in selected_fid_or_template:
                display_text = "Custom Ext Video"
            elif "{size}" in selected_fid_or_template:
                display_text = "Custom Size Video"
            else:
                display_text = "Video (Unknown)"

        elif download_type == "audio":
            selected_fid_or_template = self.audio_var.get()
            # Try to find the format in the fetched list first
            found_format = next((f for f in self.audio_formats if f[0] == selected_fid_or_template), None)
            
            if found_format:
                abr = found_format[3] # abr is 4th element (index 3)
                ext = found_format[4] # ext is 5th element (index 4)
                display_text = f"Audio {ext.upper()}"
                if abr and abr != 0:
                    display_text += f" ({abr}k)"
            # Handle default templates
            elif selected_fid_or_template == "ba":
                display_text = "Best Audio"
            elif "{ext}" in selected_fid_or_template:
                display_text = "Custom Ext Audio"
            elif "{size}" in selected_fid_or_template:
                display_text = "Custom Size Audio"
            else:
                display_text = "Audio (Unknown)"
        
        self.resolution_label.configure(text=display_text)


    def update_size(self, *args):
        """
        Updates the estimated total download size label based on selected formats.
        Formatted to match GUI style.
        """
        download_type = self.type_var.get()
        size_bytes = 0

        def find_size(fid, formats_list):
            for fid_, label, size, *rest in formats_list:
                if fid_ == fid:
                    return size
            return 0

        if download_type == "audio":
            size_bytes = find_size(self.audio_var.get(), self.audio_formats)
        elif download_type == "video":
            size_bytes = find_size(self.video_var.get(), self.video_formats)
        else:  # both
            size_bytes = (
                find_size(self.video_var.get(), self.video_formats)
                + find_size(self.audio_var.get(), self.audio_formats)
            )

        if size_bytes > 0:
            formatted = f"Estimated Size: \u2B07 {size_bytes / (1024 * 1024):.2f} MB"
            self.size_label.configure(text=formatted, font=ctk.CTkFont(size=14, weight="bold"), text_color=self.current_colors["accent_green"])
        else:
            self.size_label.configure(text="Estimated Size: ? (Fetch formats)", font=ctk.CTkFont(size=14), text_color=self.current_colors["gray_text"])

    # --- Core Downloader Logic Methods ---
    def setup_cookie_path(self):
        """
        Manages the cookies.txt file path. Ensures it exists and offers pasting
        if content is missing.
        """
        # Always use the default cookies.txt path next to the script
        default_cookie_path = os.path.abspath('cookies.txt')
        self.cookie_path = default_cookie_path # Set the instance variable

        # Check if the cookies.txt file exists and has content
        cookie_file_exists = os.path.exists(self.cookie_path)
        cookie_file_empty = True
        if cookie_file_exists:
            try:
                with open(self.cookie_path, 'r') as f:
                    content = f.read().strip()
                    if content:
                        cookie_file_empty = False
            except IOError:
                # If file exists but can't be read (e.g., permissions), treat as empty
                cookie_file_empty = True


        # If the cookie file doesn't exist or is empty, prompt the user
        if not cookie_file_exists or cookie_file_empty:
            response_for_guide = messagebox.askyesno(
                "Cookies Not Found/Empty",
                "The 'cookies.txt' file was not found or is empty.\n"
                "This file is often required for downloading age-restricted or private videos.\n\n"
                "Would you like to see a guide on how to create one and paste its content?"
            )

            if response_for_guide:
                messagebox.showinfo(
                    "Cookie Editor Guide (Steps)",
                    "To generate 'cookies.txt', please follow these steps:\n\n"
                    "1. Open your Chrome browser.\n"
                    "2. Search for 'Chrome Web Store' -> 'Cookie Editor' or go to:\n"
                    "   https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm\n"
                    "3. Add the 'Cookie Editor' extension to Chrome.\n"
                    "4. Go to youtube.com and log in to your account.\n"
                    "5. Click on the 'Cookie Editor' extension icon in your browser toolbar.\n"
                    "6. Ensure 'This site' (youtube.com) is selected within the extension.\n"
                    "7. Click 'Export' -> 'Export as Netscape'.\n"
                    "8. Copy the content.\n\n"
                    "Now, please paste the copied Netscape cookie content into the text box that will appear."
                )
            
            cookie_dialog = CookieInputDialog(
                self,
                "Paste Cookies",
                "Please paste your Netscape cookie content here and click OK:"
            )
            pasted_content = cookie_dialog.get_input() # This will block until dialog is closed

            if pasted_content:
                try:
                    with open(self.cookie_path, 'w') as f: # Overwrite the default cookies.txt
                        f.write(pasted_content)
                    self.save_settings() # Save settings (though path hasn't changed, content has)
                    messagebox.showinfo("Success", "Cookies saved successfully to cookies.txt!")
                except IOError as e:
                    messagebox.showerror("Error", f"Failed to save cookies to cookies.txt: {e}")
            else:
                messagebox.showwarning("Warning", "No cookie content provided. Downloads for some videos may fail.")
        
        # Always return the default cookie path, regardless if content was pasted or not
        return self.cookie_path

    def fetch_formats_wrapper(self):
        """
        Wrapper to initiate format fetching. Clears current options and displays "Fetching..."
        then calls the actual fetch_formats method.
        """
        # Clear previous format options and display fetching status
        self.video_format_menu.configure(values=["- Fetching... -"])
        self.audio_format_menu.configure(values=["- Fetching... -"])
        self.video_format_menu.set("- Fetching... -")
        self.audio_format_menu.set("- Fetching... -")
        self.resolution_label.configure(text="Fetching...")
        self.status_label.configure(text="Fetching formats, please wait...")
        self.update_idletasks() # Force GUI update to show "Fetching..." messages

        # Call the actual fetch_formats method. Using self.after ensures GUI updates before heavy lifting.
        self.after(100, self.fetch_formats)

    def fetch_formats(self):
        """
        Fetches available video and audio formats for the given YouTube URL using yt-dlp.
        Populates the format dropdown menus with the fetched options.
        """
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Input Error", "Please enter a YouTube URL.")
            self.status_label.configure(text="Ready")
            # Reset menus to default if no URL
            self.populate_menu(self.video_format_menu, self.video_var, [], self.get_default_video_formats())
            self.populate_menu(self.audio_format_menu, self.audio_var, [], self.get_default_audio_formats())
            self.update_resolution_label()
            return

        try:
            with yt_dlp.YoutubeDL({
                'quiet': True, # Suppress console output from yt-dlp
                'cookiefile': os.path.abspath(self.cookie_path), # Use the determined cookie path
                'noplaylist': True,
                'verbose': False,
                'quiet': True,
            }) as ydl:
                info = ydl.extract_info(url, download=False)
                # Check if it's a playlist (yt-dlp returns 'entries' for playlists)
                if 'entries' in info:
                    messagebox.showwarning("Playlist Detected", "This URL points to a playlist. Only the first video in the playlist will be processed for formats. For full playlist download, use a dedicated playlist downloader.")
                    # Take the first entry if it's a playlist
                    info = info['entries'][0] if info['entries'] else {}
                    if not info:
                        raise ValueError("No videos found in the playlist.")

                self.current_video_title = info.get('title', 'video') # Store the title here

                formats = info.get('formats', [])

            self.video_formats = []
            self.audio_formats = []

            for f in formats:
                format_id = f.get('format_id')
                ext = f.get('ext')
                height = f.get('height')
                abr = f.get('abr') # Audio bitrate

                # Construct label for display
                display_label = ""
                if f.get('vcodec') != 'none' and f.get('acodec') == 'none': # Video-only stream
                    display_label = f"{height}p {ext}" if height else f"Video {ext}"
                elif f.get('acodec') != 'none' and f.get('vcodec') == 'none': # Audio-only stream
                    display_label = f"Audio {ext} ({abr}k)" if abr else f"Audio {ext}"
                elif f.get('vcodec') != 'none' and f.get('acodec') != 'none': # Combined video and audio
                    display_label = f"{height}p {ext}" if height else f"Combined {ext}"

                filesize = f.get('filesize') or f.get('filesize_approx')
                filesize_str = f"({round(filesize / (1024 * 1024), 1)} MB)" if filesize else ""
                
                final_label = f"{display_label} ({format_id}) {filesize_str}".strip()

                if f.get('vcodec') != 'none' and f.get('acodec') == 'none': # Video-only stream
                    self.video_formats.append((format_id, final_label, filesize or 0, height, ext))
                elif f.get('acodec') != 'none' and f.get('vcodec') == 'none': # Audio-only stream
                    self.audio_formats.append((format_id, final_label, filesize or 0, abr, ext))
                elif f.get('vcodec') != 'none' and f.get('acodec') != 'none': # Combined video and audio
                    # Add combined formats to video list as well, often these are highest quality
                    self.video_formats.append((format_id, final_label, filesize or 0, height, ext))

            # Sort formats for better user experience (e.g., by resolution descending for video)
            self.video_formats.sort(key=lambda x: x[3] if x[3] is not None else -1, reverse=True) # Sort by height
            self.audio_formats.sort(key=lambda x: x[2] if x[2] is not None else -1, reverse=True) # Sort by size for audio, handle None

            # Populate the actual CTkOptionMenu widgets
            self.populate_menu(self.video_format_menu, self.video_var, self.video_formats, self.video_formats if self.video_formats else self.get_default_video_formats())
            self.populate_menu(self.audio_format_menu, self.audio_var, self.audio_formats, self.audio_formats if self.audio_formats else self.get_default_audio_formats())

            self.not_fetched_label.pack_forget() # Hide the "not fetched" label
            self.update_size() # Update estimated size
            self.status_label.configure(text="Formats fetched successfully.")
            messagebox.showinfo("Success", "Available formats fetched. Select from dropdowns.")

        except Exception as e:
            messagebox.showerror("Error", f"Could not fetch formats:\n{str(e)}\nEnsure URL is valid and cookies.txt is accessible.")
            self.status_label.configure(text="Failed to fetch formats.")
            # Revert menus to default options on error
            self.populate_menu(self.video_format_menu, self.video_var, [], self.get_default_video_formats())
            self.populate_menu(self.audio_format_menu, self.audio_var, [], self.get_default_audio_formats())
            self.update_resolution_label()


    def download(self):
        """
        Initiates the download process using yt-dlp based on selected options.
        Includes progress bar updates and error handling.
        """
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube URL before downloading.")
            return

        download_type = self.type_var.get()
        if download_type not in ["audio", "video", "both"]:
            messagebox.showerror("Error", "Please select a valid download type (Audio, Video, or Both).")
            return

        # Ask user for download folder
        out_folder = filedialog.askdirectory(title="Select download folder")
        if not out_folder:
            self.status_label.configure(text="Download cancelled by user.")
            return

        selected_video_format_id = self.video_var.get()
        selected_audio_format_id = self.audio_var.get()
        selected_convert_format = self.convert_var.get()

        ydl_opts = {
            'outtmpl': os.path.join(out_folder, f'{self.filename_entry.get() or self.current_video_title}.%(ext)s'),
            'progress_hooks': [self.download_progress_hook],
            'cookiefile': os.path.abspath(self.cookie_path), # Use the determined cookie path
            'noplaylist': True,
            'verbose': False,
            'quiet': True,
            'ffmpeg_location': get_ffmpeg_dir_for_yt_dlp(), # Use the directory path here
        }

        # Determine the format string for yt-dlp
        if download_type == "audio":
            format_string = selected_audio_format_id
            ydl_opts['format'] = format_string
            if selected_convert_format and selected_convert_format != "- Convert To -":
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': selected_convert_format,
                    'preferredquality': '192', # Default audio quality for extraction
                }]
                ydl_opts['outtmpl'] = os.path.join(out_folder, f'{self.filename_entry.get() or self.current_video_title}.{selected_convert_format}')
            else:
                ydl_opts['outtmpl'] = os.path.join(out_folder, f'{self.filename_entry.get() or self.current_video_title}.%(ext)s')

        elif download_type == "video":
            format_string = selected_video_format_id
            ydl_opts['format'] = format_string
            if selected_convert_format and selected_convert_format != "- Convert To -":
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': selected_convert_format,
                }]
                ydl_opts['outtmpl'] = os.path.join(out_folder, f'{self.filename_entry.get() or self.current_video_title}.{selected_convert_format}')
            else:
                ydl_opts['outtmpl'] = os.path.join(out_folder, f'{self.filename_entry.get() or self.current_video_title}.%(ext)s')

        elif download_type == "both":
            # For "both", we try to combine best video and best audio (if available separately)
            # or download the best combined stream.
            if selected_video_format_id != "bv" and selected_audio_format_id != "ba":
                format_string = f"{selected_video_format_id}+{selected_audio_format_id}"
            elif selected_video_format_id != "bv": # Only video selected, but user chose "both"
                 format_string = selected_video_format_id # Will download best audio if combined is not found
            elif selected_audio_format_id != "ba": # Only audio selected, but user chose "both"
                format_string = selected_audio_format_id # Will download best video if combined is not found
            else:
                format_string = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best" # Default best combined, or best single

            ydl_opts['format'] = format_string
            if selected_convert_format and selected_convert_format != "- Convert To -":
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': selected_convert_format,
                }]
                ydl_opts['outtmpl'] = os.path.join(out_folder, f'{self.filename_entry.get() or self.current_video_title}.{selected_convert_format}')
            else:
                ydl_opts['outtmpl'] = os.path.join(out_folder, f'{self.filename_entry.get() or self.current_video_title}.%(ext)s')


        self.download_button.configure(state="disabled", text="DOWNLOADING...")
        self.progress_bar.set(0)
        self.status_label.configure(text="Starting download...")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self.status_label.configure(text=f"Download complete: {self.filename_entry.get() or self.current_video_title}")
            messagebox.showinfo("Download Complete", f"Video downloaded successfully to: {out_folder}")
        except Exception as e:
            self.status_label.configure(text=f"Download failed: {str(e)}")
            messagebox.showerror("Download Error", f"An error occurred during download:\n{str(e)}")
        finally:
            self.download_button.configure(state="normal", text="DOWNLOAD")
            self.progress_bar.set(0)


    def download_progress_hook(self, d):
        """
        Progress hook for yt-dlp to update the GUI progress bar and status label.
        """
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total_bytes:
                downloaded_bytes = d.get('downloaded_bytes', 0)
                progress = downloaded_bytes / total_bytes
                self.progress_bar.set(progress)
                self.status_label.configure(text=f"Downloading: {(progress*100):.1f}% of {total_bytes / (1024*1024):.2f} MB")
            else:
                # If total_bytes is not available, just show general downloading status
                self.status_label.configure(text="Downloading...")
            self.update_idletasks() # Force GUI update
        elif d['status'] == 'finished':
            self.progress_bar.set(1)
            self.status_label.configure(text="Post-processing...")
            self.update_idletasks()
        elif d['status'] == 'error':
            self.status_label.configure(text=f"Download error: {d.get('error', 'Unknown error')}")
            self.progress_bar.set(0)
            self.update_idletasks()

    def paste_clipboard(self):
        """Pastes content from the clipboard into the URL entry field."""
        try:
            clipboard_content = pyperclip.paste()
            self.url_entry.delete(0, ctk.END)
            self.url_entry.insert(0, clipboard_content)
        except Exception as e:
            messagebox.showerror("Clipboard Error", f"Failed to paste from clipboard: {e}")

    # --- Custom Window Dragging Functionality ---
    # These methods allow dragging the custom-framed window.
    def start_drag(self, event):
        """Records the starting position of the mouse for dragging."""
        self.x = event.x
        self.y = event.y

    def do_drag(self, event):
        """Moves the window as the mouse is dragged."""
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.winfo_x() + deltax
        y = self.winfo_y() + deltay
        self.geometry(f"+{x}+{y}")

# --- Main Execution Block ---
if __name__ == "__main__":
    # Set high DPI awareness for better scaling on Windows (optional but recommended)
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass # Not on Windows or an older version

    app = App()
    app.mainloop()

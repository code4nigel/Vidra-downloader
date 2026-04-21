import os

# --- APP INFO ---
APP_NAME = "Vidra"
VERSION = "2.7.3"

# --- THEME (Samsung One UI Inspired) ---
ACCENT_COLOR = "#00FFAA"
DANGER_COLOR = "#FF4B4B"
BG_SIDEBAR = ("#E8EAED", "#000000")
BG_MAIN = ("#F4F6F8", "#0A0A0A")
BG_CARD = ("#FFFFFF", "#1A1A1A")
TEXT_PRIMARY = ("#000000", "#FFFFFF")
TEXT_MUTED = ("#666666", "#888888")
BTN_BG = ("#E0E0E0", "#222222")
BTN_HOVER = ("#D0D0D0", "#333333")

# --- FILE PATHS ---
SETTINGS_FILE = "vidra_config.json"
HISTORY_FILE = "vidra_history.json"
COOKIE_FILE = os.path.abspath("cookies.txt")

# --- DEPENDENCIES ---
REQUIRED_MODULES = [
    "yt_dlp", 
    "pyperclip", 
    "customtkinter", 
    "Pillow", 
    "requests", 
    "mutagen"
]

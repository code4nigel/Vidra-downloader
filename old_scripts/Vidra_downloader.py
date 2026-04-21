import customtkinter as ctk
from PIL import Image
import yt_dlp
import pyperclip
import os
import sys
import threading
import json
import subprocess
import ctypes
from tkinter import filedialog, messagebox
from queue import Queue

# --- CONFIG & THEME ---
APP_NAME = "Vidra"
VERSION = "2.0.1"
ACCENT_COLOR = "#00FFAA"
DANGER_COLOR = "#FF4B4B"
BG_MAIN = "#121212"
BG_CARD = "#1E1E1E"
REQUIRED_MODULES = ["yt_dlp", "pyperclip", "customtkinter"]

# --- HELPERS ---
def ensure_packages():
    updated = False
    for module in REQUIRED_MODULES:
        try:
            __import__(module)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", module])
            updated = True
    return updated

# --- DOWNLOAD LOGIC ENGINE ---
class DownloadEngine:
    def __init__(self, cookie_path):
        self.cookie_path = cookie_path

    def get_info(self, url):
        ydl_opts = {
            'quiet': True,
            'cookiefile': self.cookie_path if os.path.exists(self.cookie_path) else None,
            'noplaylist': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    def download(self, url, opts, progress_hook):
        opts['progress_hooks'] = [progress_hook]
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

# --- UI COMPONENTS ---
class DownloadCard(ctk.CTkFrame):
    def __init__(self, master, job_id, title, **kwargs):
        super().__init__(master, fg_color=BG_CARD, corner_radius=12, **kwargs)
        self.grid_columnconfigure(1, weight=1)
        
        self.status_icon = ctk.CTkLabel(self, text="⏳", font=("Segoe UI", 20))
        self.status_icon.grid(row=0, column=0, rowspan=2, padx=15, pady=10)
        
        display_title = (title[:45] + '..') if len(title) > 45 else title
        self.title_label = ctk.CTkLabel(self, text=display_title, font=("Segoe UI", 13, "bold"), anchor="w")
        self.title_label.grid(row=0, column=1, sticky="ew", pady=(10, 0))
        
        self.p_bar = ctk.CTkProgressBar(self, height=6, progress_color=ACCENT_COLOR, fg_color="#333333")
        self.p_bar.grid(row=1, column=1, sticky="ew", padx=(0, 15), pady=5)
        self.p_bar.set(0)
        
        self.stats_label = ctk.CTkLabel(self, text="Initializing...", font=("Segoe UI", 10), text_color="#888888")
        self.stats_label.grid(row=2, column=1, sticky="w", pady=(0, 10))

    def update_progress(self, progress, speed, eta, status_text=None):
        self.p_bar.set(progress)
        if status_text:
            self.stats_label.configure(text=status_text)
        else:
            self.stats_label.configure(text=f"Speed: {speed} | ETA: {eta}")
        
        if progress >= 1:
            self.status_icon.configure(text="✅")
            self.stats_label.configure(text="Complete", text_color=ACCENT_COLOR)

# --- MAIN APPLICATION ---
class VidraApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ensure_packages()

        self.title(f"{APP_NAME} Pro")
        self.geometry("1000x680")
        ctk.set_appearance_mode("Dark")
        
        self.engine = DownloadEngine(os.path.abspath("cookies.txt"))
        self.update_queue = Queue()
        self.cards = {}
        self.job_counter = 0
        self.drag_data = {"x": 0, "y": 0}

        self.setup_ui()
        self.check_queue()

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. SIDEBAR
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#0A0A0A")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # Sidebar Drag Support
        self.sidebar.bind("<ButtonPress-1>", self.start_drag)
        self.sidebar.bind("<B1-Motion>", self.do_drag)
        
        logo = ctk.CTkLabel(self.sidebar, text=APP_NAME, font=("Segoe UI", 32, "bold"), text_color=ACCENT_COLOR)
        logo.pack(pady=(40, 30))
        logo.bind("<ButtonPress-1>", self.start_drag)
        logo.bind("<B1-Motion>", self.do_drag)
        
        self.btn_download = self.create_nav_btn("📥 Downloader", self.show_downloader)
        self.btn_manage = self.create_nav_btn("📋 Manage", self.show_manage)
        
        ctk.CTkLabel(self.sidebar, text="", height=1).pack(expand=True) # Spacer
        
        self.create_nav_btn("🔄 Update Modules", self.update_deps)
        self.create_nav_btn("❌ Exit", self.destroy)

        # 2. CONTENT AREA
        self.container = ctk.CTkFrame(self, corner_radius=0, fg_color=BG_MAIN)
        self.container.grid(row=0, column=1, sticky="nsew")
        
        # PAGE: DOWNLOADER
        self.page_dl = ctk.CTkFrame(self.container, fg_color="transparent")
        self.setup_downloader_page()
        
        # PAGE: MANAGE
        self.page_manage = ctk.CTkFrame(self.container, fg_color="transparent")
        ctk.CTkLabel(self.page_manage, text="Active Downloads", font=("Segoe UI", 20, "bold")).pack(pady=(20, 0), padx=30, anchor="w")
        self.scroll_frame = ctk.CTkScrollableFrame(self.page_manage, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.show_downloader()

    def setup_downloader_page(self):
        content = ctk.CTkFrame(self.page_dl, fg_color="transparent")
        content.place(relx=0.5, rely=0.45, anchor="center", relwidth=0.85)

        ctk.CTkLabel(content, text="Streamline your downloads", font=("Segoe UI", 24, "bold")).pack(pady=10)
        
        # URL Input
        input_frame = ctk.CTkFrame(content, height=54, corner_radius=27, fg_color=BG_CARD)
        input_frame.pack(fill="x", pady=10)
        
        self.url_entry = ctk.CTkEntry(input_frame, placeholder_text="Enter YouTube or Video URL...", border_width=0, fg_color="transparent", height=54, font=("Segoe UI", 14))
        self.url_entry.pack(side="left", fill="x", expand=True, padx=20)
        
        ctk.CTkButton(input_frame, text="Paste", width=70, height=32, corner_radius=16, fg_color="#333333", hover_color="#444444", command=self.paste_link).pack(side="right", padx=10)

        # OPTIONS GRID
        opts_frame = ctk.CTkFrame(content, fg_color="transparent")
        opts_frame.pack(fill="x", pady=15)
        
        # Format Type
        self.type_var = ctk.StringVar(value="both")
        type_box = ctk.CTkFrame(opts_frame, fg_color=BG_CARD, corner_radius=12, height=45)
        type_box.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        ctk.CTkRadioButton(type_box, text="Video", variable=self.type_var, value="both", font=("Segoe UI", 12)).pack(side="left", padx=15, pady=10)
        ctk.CTkRadioButton(type_box, text="Audio Only", variable=self.type_var, value="audio", font=("Segoe UI", 12)).pack(side="left", padx=10)

        # Extension / Quality
        self.ext_var = ctk.StringVar(value="mp4")
        self.ext_menu = ctk.CTkOptionMenu(opts_frame, values=["mp4", "mkv", "mp3", "m4a", "wav"], variable=self.ext_var, fg_color=BG_CARD, button_color="#333333", width=120, height=45, corner_radius=12)
        self.ext_menu.pack(side="right")

        # START BUTTON
        self.dl_btn = ctk.CTkButton(content, text="START DOWNLOAD", height=50, width=280, corner_radius=25, font=("Segoe UI", 15, "bold"), fg_color=DANGER_COLOR, hover_color="#E03A3A", command=self.handle_start)
        self.dl_btn.pack(pady=20)

    # --- LOGIC & ACTIONS ---
    def start_drag(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def do_drag(self, event):
        x = self.winfo_x() + (event.x - self.drag_data["x"])
        y = self.winfo_y() + (event.y - self.drag_data["y"])
        self.geometry(f"+{x}+{y}")

    def create_nav_btn(self, text, command):
        btn = ctk.CTkButton(self.sidebar, text=text, font=("Segoe UI", 13), anchor="w", fg_color="transparent", hover_color="#1A1A1A", height=45, corner_radius=8, command=command)
        btn.pack(fill="x", padx=12, pady=3)
        return btn

    def show_downloader(self):
        self.page_manage.pack_forget()
        self.page_dl.pack(fill="both", expand=True)

    def show_manage(self):
        self.page_dl.pack_forget()
        self.page_manage.pack(fill="both", expand=True)

    def paste_link(self):
        self.url_entry.delete(0, 'end')
        self.url_entry.insert(0, pyperclip.paste())

    def update_deps(self):
        if messagebox.askyesno("Update", "Update yt-dlp and core modules?"):
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade"] + REQUIRED_MODULES)
                messagebox.showinfo("Success", "Modules updated. Please restart Vidra.")
            except Exception as e:
                messagebox.showerror("Error", f"Update failed: {e}")

    def handle_start(self):
        url = self.url_entry.get().strip()
        if not url: return

        folder = filedialog.askdirectory()
        if not folder: return

        self.job_counter += 1
        jid = self.job_counter
        
        card = DownloadCard(self.scroll_frame, jid, "Initializing connection...")
        card.pack(fill="x", pady=5, padx=10)
        self.cards[jid] = card
        
        self.show_manage()
        threading.Thread(target=self.run_download, args=(jid, url, folder), daemon=True).start()

    def run_download(self, jid, url, folder):
        try:
            info = self.engine.get_info(url)
            title = info.get('title', 'Video')
            self.update_queue.put(('title', jid, title))
            
            ext = self.ext_var.get()
            mode = self.type_var.get()

            opts = {
                'outtmpl': os.path.join(folder, f"{title}.%(ext)s"),
            }

            if mode == 'audio':
                opts['format'] = 'bestaudio/best'
                opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': ext if ext in ['mp3', 'wav', 'm4a'] else 'mp3',
                    'preferredquality': '192',
                }]
            else:
                opts['format'] = f'bestvideo+bestaudio/best'
                if ext != 'mp4': # Conversion logic
                     opts['postprocessors'] = [{'key': 'FFmpegVideoConvertor', 'preferedformat': ext}]

            def hook(d):
                if d['status'] == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 1)
                    p = d.get('downloaded_bytes', 0) / total
                    speed = d.get('_speed_str', 'N/A')
                    eta = d.get('_eta_str', 'N/A')
                    self.update_queue.put(('progress', jid, (p, speed, eta)))
                elif d['status'] == 'finished':
                    self.update_queue.put(('progress', jid, (1.0, "0", "0")))

            self.engine.download(url, opts, hook)
        except Exception as e:
            self.update_queue.put(('error', jid, str(e)))

    def check_queue(self):
        while not self.update_queue.empty():
            msg_type, jid, data = self.update_queue.get()
            card = self.cards.get(jid)
            if not card: continue

            if msg_type == 'title':
                card.title_label.configure(text=data)
            elif msg_type == 'progress':
                p, s, e = data
                card.update_progress(p, s, e)
            elif msg_type == 'error':
                card.update_progress(0, "", "", f"Error: {data}")
        self.after(100, self.check_queue)

if __name__ == "__main__":
    if sys.platform == "win32":
        try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except: pass
    app = VidraApp()
    app.mainloop()
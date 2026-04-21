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
VERSION = "2.2.1"
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
        self.geometry("1000x750")
        ctk.set_appearance_mode("Dark")
        
        self.engine = DownloadEngine(os.path.abspath("cookies.txt"))
        self.update_queue = Queue()
        self.cards = {}
        self.job_counter = 0
        self.drag_data = {"x": 0, "y": 0}
        
        # State for dynamic formats
        self.available_video = []
        self.available_audio = []

        self.setup_ui()
        self.check_queue()

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. SIDEBAR
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#0A0A0A")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.bind("<ButtonPress-1>", self.start_drag)
        self.sidebar.bind("<B1-Motion>", self.do_drag)
        
        logo = ctk.CTkLabel(self.sidebar, text=APP_NAME, font=("Segoe UI", 32, "bold"), text_color=ACCENT_COLOR)
        logo.pack(pady=(40, 30))
        logo.bind("<ButtonPress-1>", self.start_drag)
        logo.bind("<B1-Motion>", self.do_drag)
        
        self.create_nav_btn("📥 Downloader", self.show_downloader)
        self.create_nav_btn("📋 Manage", self.show_manage)
        ctk.CTkLabel(self.sidebar, text="", height=1).pack(expand=True)
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
        content.place(relx=0.5, rely=0.45, anchor="center", relwidth=0.88)

        self.dl_status_header = ctk.CTkLabel(content, text="Streamline your downloads", font=("Segoe UI", 24, "bold"))
        self.dl_status_header.pack(pady=10)
        
        # URL Input
        input_frame = ctk.CTkFrame(content, height=56, corner_radius=28, fg_color=BG_CARD)
        input_frame.pack(fill="x", pady=10)
        
        self.url_entry = ctk.CTkEntry(input_frame, placeholder_text="Paste your link here...", border_width=0, fg_color="transparent", height=56, font=("Segoe UI", 14))
        self.url_entry.pack(side="left", fill="x", expand=True, padx=20)
        self.url_entry.bind("<KeyRelease>", self.on_url_change)
        
        ctk.CTkButton(input_frame, text="Paste & Analyze", width=120, height=36, corner_radius=18, fg_color="#333333", hover_color="#444444", command=self.paste_and_analyze).pack(side="right", padx=10)

        # SELECTION CONTROLS
        sel_frame = ctk.CTkFrame(content, fg_color="transparent")
        sel_frame.pack(fill="x", pady=10)
        
        # Mode Switcher (Video/Audio/Both)
        self.mode_var = ctk.StringVar(value="Both")
        self.mode_switch = ctk.CTkSegmentedButton(
            sel_frame, 
            values=["Video", "Audio", "Both"], 
            variable=self.mode_var, 
            height=45, 
            corner_radius=25, 
            selected_color=ACCENT_COLOR, 
            unselected_color=BG_CARD, 
            selected_hover_color=ACCENT_COLOR, 
            command=self.update_ui_state
        )
        self.mode_switch.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # Extension Dropdown
        self.ext_var = ctk.StringVar(value="mp4")
        self.ext_menu = ctk.CTkOptionMenu(sel_frame, values=["mp4", "mkv", "webm", "mp3", "m4a", "wav"], variable=self.ext_var, fg_color=BG_CARD, button_color="#333333", width=110, height=45, corner_radius=12)
        self.ext_menu.pack(side="right")

        # QUALITY DROPDOWNS (Dynamic)
        self.quality_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.quality_frame.pack(fill="x", pady=5)
        
        self.v_qual_var = ctk.StringVar(value="Best Video")
        self.v_qual_menu = ctk.CTkOptionMenu(self.quality_frame, values=["Best Video"], variable=self.v_qual_var, fg_color=BG_CARD, button_color="#333333", height=45, corner_radius=12)
        self.v_qual_menu.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.a_qual_var = ctk.StringVar(value="Best Audio")
        self.a_qual_menu = ctk.CTkOptionMenu(self.quality_frame, values=["Best Audio"], variable=self.a_qual_var, fg_color=BG_CARD, button_color="#333333", height=45, corner_radius=12)
        self.a_qual_menu.pack(side="right", fill="x", expand=True, padx=(5, 0))

        # FILENAME / RENAMING INPUT
        rename_frame = ctk.CTkFrame(content, height=50, corner_radius=12, fg_color=BG_CARD)
        rename_frame.pack(fill="x", pady=(15, 0))
        self.rename_entry = ctk.CTkEntry(rename_frame, placeholder_text="Set custom filename (Optional)", border_width=0, fg_color="transparent", height=50, font=("Segoe UI", 13))
        self.rename_entry.pack(fill="x", padx=15)

        # START BUTTON
        self.dl_btn = ctk.CTkButton(content, text="START DOWNLOAD", height=54, width=300, corner_radius=27, font=("Segoe UI", 16, "bold"), fg_color=DANGER_COLOR, hover_color="#E03A3A", command=self.handle_start)
        self.dl_btn.pack(pady=25)

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

    def update_ui_state(self, choice):
        if choice == "Audio":
            self.v_qual_menu.configure(state="disabled")
            self.a_qual_menu.configure(state="normal")
            if self.ext_var.get() in ["mp4", "mkv"]: self.ext_var.set("mp3")
        elif choice == "Video":
            self.v_qual_menu.configure(state="normal")
            self.a_qual_menu.configure(state="disabled")
            if self.ext_var.get() in ["mp3", "m4a"]: self.ext_var.set("mp4")
        else:
            self.v_qual_menu.configure(state="normal")
            self.a_qual_menu.configure(state="normal")

    def on_url_change(self, event):
        # Optional: Auto-fetch on change with a debounce
        pass

    def paste_and_analyze(self):
        self.url_entry.delete(0, 'end')
        self.url_entry.insert(0, pyperclip.paste().strip())
        self.fetch_formats()

    def fetch_formats(self):
        url = self.url_entry.get().strip()
        if not url: return
        
        self.dl_status_header.configure(text="Analyzing Link... 🔍", text_color=ACCENT_COLOR)
        threading.Thread(target=self.run_fetch, args=(url,), daemon=True).start()

    def run_fetch(self, url):
        try:
            info = self.engine.get_info(url)
            formats = info.get('formats', [])
            
            v_list = []
            a_list = []
            
            for f in formats:
                fid = f.get('format_id')
                ext = f.get('ext')
                # Video Filter
                if f.get('vcodec') != 'none' and f.get('height'):
                    res = f"{f['height']}p ({ext})"
                    if res not in [x[1] for x in v_list]:
                        v_list.append((fid, res))
                # Audio Filter
                if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    abr = f.get('abr')
                    bit = f"{int(abr)}k" if abr else "N/A"
                    label = f"{bit} ({ext})"
                    if label not in [x[1] for x in a_list]:
                        a_list.append((fid, label))

            self.update_queue.put(('formats_ready', 0, (v_list, a_list)))
        except Exception as e:
            self.update_queue.put(('error_header', 0, str(e)))

    def handle_start(self):
        url = self.url_entry.get().strip()
        if not url: return
        folder = filedialog.askdirectory()
        if not folder: return

        custom_name = self.rename_entry.get().strip()

        self.job_counter += 1
        jid = self.job_counter
        
        card = DownloadCard(self.scroll_frame, jid, "Awaiting Metadata...")
        card.pack(fill="x", pady=5, padx=10)
        self.cards[jid] = card
        
        self.show_manage()
        threading.Thread(target=self.run_download, args=(jid, url, folder, custom_name), daemon=True).start()

    def run_download(self, jid, url, folder, custom_name):
        try:
            info = self.engine.get_info(url)
            title = custom_name if custom_name else info.get('title', 'Video')
            self.update_queue.put(('title', jid, title))
            
            mode = self.mode_var.get()
            ext = self.ext_var.get()
            
            opts = {'outtmpl': os.path.join(folder, f"{title}.%(ext)s")}

            if mode == "Audio":
                opts['format'] = 'bestaudio/best'
                opts['postprocessors'] = [{'key': 'FFmpegExtractAudio','preferredcodec': ext if ext in ['mp3','wav','m4a'] else 'mp3','preferredquality': '192'}]
            elif mode == "Video":
                opts['format'] = 'bestvideo/best'
                if ext != 'mp4': opts['postprocessors'] = [{'key': 'FFmpegVideoConvertor', 'preferedformat': ext}]
            else:
                opts['format'] = 'bestvideo+bestaudio/best'

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
            
            if msg_type == 'formats_ready':
                v_list, a_list = data
                self.v_qual_menu.configure(values=[x[1] for x in v_list] if v_list else ["Best Video"])
                self.a_qual_menu.configure(values=[x[1] for x in a_list] if a_list else ["Best Audio"])
                self.dl_status_header.configure(text="Analysis Complete ✅", text_color="white")
            elif msg_type == 'error_header':
                self.dl_status_header.configure(text="Analysis Failed ❌", text_color=DANGER_COLOR)
            
            card = self.cards.get(jid)
            if card:
                if msg_type == 'title': card.title_label.configure(text=data)
                elif msg_type == 'progress':
                    p, s, e = data
                    card.update_progress(p, s, e)
                elif msg_type == 'error': card.update_progress(0, "", "", f"Error: {data}")
        
        self.after(100, self.check_queue)

    def update_deps(self):
        if messagebox.askyesno("Update", "Update yt-dlp and core modules?"):
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade"] + REQUIRED_MODULES)
            messagebox.showinfo("Success", "Modules updated. Please restart Vidra.")

if __name__ == "__main__":
    if sys.platform == "win32":
        try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except: pass
    app = VidraApp()
    app.mainloop()
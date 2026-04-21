import customtkinter as ctk
from PIL import Image
import yt_dlp
import pyperclip
import os
import sys
import threading
import subprocess
import ctypes
import requests
import json
from io import BytesIO
from tkinter import filedialog, messagebox
from queue import Queue

# --- CONFIG & THEME (Samsung One UI Inspired) ---
APP_NAME = "Vidra"
VERSION = "2.4.0"
ACCENT_COLOR = "#00FFAA"
DANGER_COLOR = "#FF4B4B"
BG_SIDEBAR = "#000000"
BG_MAIN = "#0A0A0A"
BG_CARD = "#1A1A1A"
SETTINGS_FILE = "vidra_config.json"
HISTORY_FILE = "vidra_history.json"
REQUIRED_MODULES = ["yt_dlp", "pyperclip", "customtkinter", "Pillow", "requests"]

# --- HELPERS ---
def ensure_packages():
    for module in REQUIRED_MODULES:
        try:
            name = "PIL" if module == "Pillow" else module
            __import__(name)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", module])

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
    def __init__(self, master, job_id, title, folder, stop_callback, delete_callback, **kwargs):
        super().__init__(master, fg_color=BG_CARD, corner_radius=18, **kwargs)
        self.job_id = job_id
        self.folder = folder
        self.stop_callback = stop_callback
        self.delete_callback = delete_callback
        self.finished = False
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)
        
        self.thumb_label = ctk.CTkLabel(self, text="", width=120, height=68, fg_color="#222222", corner_radius=12)
        self.thumb_label.grid(row=0, column=0, rowspan=2, padx=15, pady=15)
        
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=1, sticky="ew", pady=(15, 0))
        
        self.platform_icon = ctk.CTkLabel(header_frame, text="🌐", font=("Segoe UI", 12))
        self.platform_icon.pack(side="left", padx=(0, 5))
        
        display_title = (title[:50] + '..') if len(title) > 50 else title
        self.title_label = ctk.CTkLabel(header_frame, text=display_title, font=("Segoe UI", 14, "bold"), anchor="w")
        self.title_label.pack(side="left", fill="x")
        
        self.p_bar = ctk.CTkProgressBar(self, height=8, progress_color=ACCENT_COLOR, fg_color="#333333")
        self.p_bar.grid(row=1, column=1, sticky="ew", padx=(0, 20), pady=5)
        self.p_bar.set(0)
        
        self.stats_label = ctk.CTkLabel(self, text="Waiting...", font=("Segoe UI", 11), text_color="#AAAAAA")
        self.stats_label.grid(row=2, column=1, sticky="w", pady=(0, 15))

        self.actions = ctk.CTkFrame(self, fg_color="transparent")
        self.actions.grid(row=0, column=2, rowspan=3, padx=15)
        
        self.folder_btn = ctk.CTkButton(self.actions, text="📁", width=35, height=35, corner_radius=10, fg_color="#333333", hover_color="#444444", command=self.open_folder)
        self.folder_btn.pack(pady=5)
        
        self.action_btn = ctk.CTkButton(self.actions, text="🛑", width=35, height=35, corner_radius=10, fg_color="#442222", hover_color=DANGER_COLOR, command=self.handle_action)
        self.action_btn.pack(pady=5)

    def set_thumbnail(self, url):
        try:
            response = requests.get(url, timeout=5)
            img_data = BytesIO(response.content)
            img = Image.open(img_data)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(120, 68))
            self.thumb_label.configure(image=ctk_img, text="")
        except:
            self.thumb_label.configure(text="No Preview")

    def update_progress(self, progress, speed, eta, status_text=None):
        self.p_bar.set(progress)
        if status_text:
            self.stats_label.configure(text=status_text)
        else:
            self.stats_label.configure(text=f"Speed: {speed} | ETA: {eta}")
        
        if progress >= 1 and not self.finished:
            self.finished = True
            self.stats_label.configure(text="Finished", text_color=ACCENT_COLOR)
            self.action_btn.configure(text="🗑️", fg_color="#333333", hover_color=DANGER_COLOR)

    def open_folder(self):
        if os.path.exists(self.folder):
            os.startfile(self.folder)

    def handle_action(self):
        if self.finished:
            self.delete_callback(self.job_id)
        else:
            self.stop_callback(self.job_id)
            self.stats_label.configure(text="Stopped", text_color=DANGER_COLOR)

# --- MAIN APPLICATION ---
class VidraApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ensure_packages()

        self.title(f"{APP_NAME} Pro")
        self.geometry("1100x850")
        ctk.set_appearance_mode("Dark")
        
        self.load_prefs()
        self.engine = DownloadEngine(os.path.abspath("cookies.txt"))
        self.update_queue = Queue()
        self.cards = {}
        self.job_counter = 0
        self.drag_data = {"x": 0, "y": 0}
        self.logo_angle = 0
        
        self.video_map = {}
        self.audio_map = {}

        self.setup_ui()
        self.animate_logo()
        self.check_queue()
        self.load_history()

    def load_prefs(self):
        defaults = {"embed_thumb": True, "keep_history": True}
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    self.prefs = {**defaults, **json.load(f)}
            except: self.prefs = defaults
        else: self.prefs = defaults

    def save_prefs(self):
        with open(SETTINGS_FILE, "w") as f:
            json.dump(self.prefs, f)

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. SIDEBAR
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=BG_SIDEBAR)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.bind("<ButtonPress-1>", self.start_drag)
        self.sidebar.bind("<B1-Motion>", self.do_drag)
        
        self.logo_label = ctk.CTkLabel(self.sidebar, text="V", font=("Segoe UI", 48, "bold"), text_color=ACCENT_COLOR)
        self.logo_label.pack(pady=(50, 10))
        
        logo_text = ctk.CTkLabel(self.sidebar, text=APP_NAME, font=("Segoe UI", 24, "bold"), text_color="white")
        logo_text.pack(pady=(0, 40))
        
        self.create_nav_btn("📥 Downloader", self.show_downloader)
        self.create_nav_btn("📋 Manage", self.show_manage)
        self.create_nav_btn("⚙️ Preferences", self.show_prefs)
        ctk.CTkLabel(self.sidebar, text="", height=1).pack(expand=True)
        self.create_nav_btn("🔄 Update", self.update_deps)
        self.create_nav_btn("❌ Exit", self.destroy)

        # 2. CONTENT AREA
        self.container = ctk.CTkFrame(self, corner_radius=0, fg_color=BG_MAIN)
        self.container.grid(row=0, column=1, sticky="nsew")
        
        # PAGE: DOWNLOADER
        self.page_dl = ctk.CTkFrame(self.container, fg_color="transparent")
        self.setup_downloader_page()
        
        # PAGE: MANAGE
        self.page_manage = ctk.CTkFrame(self.container, fg_color="transparent")
        manage_header = ctk.CTkFrame(self.page_manage, fg_color="transparent")
        manage_header.pack(fill="x", pady=(30, 10), padx=40)
        ctk.CTkLabel(manage_header, text="Downloads", font=("Segoe UI", 28, "bold")).pack(side="left")
        ctk.CTkButton(manage_header, text="Clear History", width=100, height=32, corner_radius=16, fg_color="#222222", hover_color=DANGER_COLOR, command=self.clear_history).pack(side="right")
        
        self.scroll_frame = ctk.CTkScrollableFrame(self.page_manage, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=30, pady=10)

        # PAGE: PREFERENCES
        self.page_prefs = ctk.CTkFrame(self.container, fg_color="transparent")
        self.setup_prefs_page()
        
        self.show_downloader()

    def setup_downloader_page(self):
        content = ctk.CTkFrame(self.page_dl, fg_color="transparent")
        content.place(relx=0.5, rely=0.48, anchor="center", relwidth=0.9)

        self.dl_status_header = ctk.CTkLabel(content, text="Ready to Download", font=("Segoe UI", 32, "bold"))
        self.dl_status_header.pack(pady=(20, 5))
        
        # Live Quality Indicator
        self.quality_indicator = ctk.CTkLabel(content, text="No format selected", font=("Segoe UI", 13), text_color=ACCENT_COLOR)
        self.quality_indicator.pack(pady=(0, 15))
        
        input_container = ctk.CTkFrame(content, height=64, corner_radius=32, fg_color=BG_CARD, border_width=1, border_color="#333333")
        input_container.pack(fill="x", pady=10)
        
        self.url_entry = ctk.CTkEntry(input_container, placeholder_text="Paste video link...", border_width=0, fg_color="transparent", height=64, font=("Segoe UI", 16))
        self.url_entry.pack(side="left", fill="x", expand=True, padx=25)
        
        ctk.CTkButton(input_container, text="Analyze", width=110, height=40, corner_radius=20, fg_color=ACCENT_COLOR, text_color="black", font=("Segoe UI", 14, "bold"), hover_color="#00CC88", command=self.paste_and_analyze).pack(side="right", padx=12)

        sw_frame = ctk.CTkFrame(content, fg_color="transparent")
        sw_frame.pack(fill="x", pady=20)
        
        self.mode_var = ctk.StringVar(value="Both")
        self.mode_switch = ctk.CTkSegmentedButton(sw_frame, values=["Video", "Audio", "Both"], variable=self.mode_var, height=50, corner_radius=25, fg_color="#000000", selected_color=ACCENT_COLOR, unselected_color=BG_CARD, command=self.update_ui_state)
        self.mode_switch.pack(side="left", fill="x", expand=True, padx=(0, 15))
        
        self.ext_var = ctk.StringVar(value="mp4")
        self.ext_menu = ctk.CTkOptionMenu(sw_frame, values=["mp4", "mkv", "webm", "mp3", "m4a"], variable=self.ext_var, fg_color=BG_CARD, button_color="#222222", width=120, height=50, corner_radius=15)
        self.ext_menu.pack(side="right")

        self.quality_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.quality_frame.pack(fill="x", pady=5)
        self.v_qual_var = ctk.StringVar(value="Best Video")
        self.v_qual_menu = ctk.CTkOptionMenu(self.quality_frame, values=["Best Video"], variable=self.v_qual_var, fg_color=BG_CARD, button_color="#222222", height=48, corner_radius=15, command=lambda _: self.update_quality_indicator())
        self.v_qual_menu.pack(side="left", fill="x", expand=True, padx=(0, 7))
        self.a_qual_var = ctk.StringVar(value="Best Audio")
        self.a_qual_menu = ctk.CTkOptionMenu(self.quality_frame, values=["Best Audio"], variable=self.a_qual_var, fg_color=BG_CARD, button_color="#222222", height=48, corner_radius=15, command=lambda _: self.update_quality_indicator())
        self.a_qual_menu.pack(side="right", fill="x", expand=True, padx=(7, 0))

        self.rename_entry = ctk.CTkEntry(content, placeholder_text="Custom filename (Optional)", height=54, corner_radius=15, fg_color=BG_CARD, border_width=0, font=("Segoe UI", 14))
        self.rename_entry.pack(fill="x", pady=20)

        self.dl_btn = ctk.CTkButton(content, text="DOWNLOAD", height=60, width=320, corner_radius=30, font=("Segoe UI", 18, "bold"), fg_color=DANGER_COLOR, hover_color="#E03A3A", command=self.handle_start)
        self.dl_btn.pack(pady=10)

    def setup_prefs_page(self):
        ctk.CTkLabel(self.page_prefs, text="Preferences", font=("Segoe UI", 28, "bold")).pack(pady=(30, 20), padx=40, anchor="w")
        
        container = ctk.CTkFrame(self.page_prefs, fg_color=BG_CARD, corner_radius=20)
        container.pack(fill="x", padx=40, pady=10)

        self.check_thumb = ctk.CTkCheckBox(container, text="Embed Thumbnails into Downloaded Files", font=("Segoe UI", 14), fg_color=ACCENT_COLOR, hover_color="#00CC88", command=self.update_pref_vars)
        if self.prefs["embed_thumb"]: self.check_thumb.select()
        self.check_thumb.pack(anchor="w", padx=30, pady=20)

        self.check_history = ctk.CTkCheckBox(container, text="Keep Download History Persistent", font=("Segoe UI", 14), fg_color=ACCENT_COLOR, hover_color="#00CC88", command=self.update_pref_vars)
        if self.prefs["keep_history"]: self.check_history.select()
        self.check_history.pack(anchor="w", padx=30, pady=(0, 20))

    def update_pref_vars(self):
        self.prefs["embed_thumb"] = bool(self.check_thumb.get())
        self.prefs["keep_history"] = bool(self.check_history.get())
        self.save_prefs()

    def update_quality_indicator(self):
        mode = self.mode_var.get()
        if mode == "Video": txt = f"Target: {self.v_qual_var.get()}"
        elif mode == "Audio": txt = f"Target: {self.a_qual_var.get()}"
        else: txt = f"Target: {self.v_qual_var.get()} + {self.a_qual_var.get()}"
        self.quality_indicator.configure(text=txt)

    def animate_logo(self):
        colors = ["#00FFAA", "#00E099", "#00CC88", "#00B277"]
        idx = int((self.logo_angle / 10) % len(colors))
        self.logo_label.configure(text_color=colors[idx])
        self.logo_angle += 1
        self.after(100, self.animate_logo)

    def start_drag(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def do_drag(self, event):
        x = self.winfo_x() + (event.x - self.drag_data["x"])
        y = self.winfo_y() + (event.y - self.drag_data["y"])
        self.geometry(f"+{x}+{y}")

    def create_nav_btn(self, text, command):
        btn = ctk.CTkButton(self.sidebar, text=text, font=("Segoe UI", 14), anchor="w", fg_color="transparent", hover_color="#1A1A1A", height=50, corner_radius=10, command=command)
        btn.pack(fill="x", padx=15, pady=5)
        return btn

    def show_downloader(self):
        self.page_manage.pack_forget()
        self.page_prefs.pack_forget()
        self.page_dl.pack(fill="both", expand=True)

    def show_manage(self):
        self.page_dl.pack_forget()
        self.page_prefs.pack_forget()
        self.page_manage.pack(fill="both", expand=True)

    def show_prefs(self):
        self.page_dl.pack_forget()
        self.page_manage.pack_forget()
        self.page_prefs.pack(fill="both", expand=True)

    def update_ui_state(self, choice):
        if choice == "Audio":
            self.v_qual_menu.configure(state="disabled")
            self.a_qual_menu.configure(state="normal")
        elif choice == "Video":
            self.v_qual_menu.configure(state="normal")
            self.a_qual_menu.configure(state="disabled")
        else:
            self.v_qual_menu.configure(state="normal")
            self.a_qual_menu.configure(state="normal")
        self.update_quality_indicator()

    def paste_and_analyze(self):
        self.url_entry.delete(0, 'end')
        self.url_entry.insert(0, pyperclip.paste().strip())
        url = self.url_entry.get().strip()
        if not url: return
        self.dl_status_header.configure(text="Analyzing... 🔍", text_color=ACCENT_COLOR)
        threading.Thread(target=self.run_fetch, args=(url,), daemon=True).start()

    def run_fetch(self, url):
        try:
            info = self.engine.get_info(url)
            formats = info.get('formats', [])
            v_list, a_list = [], []
            self.video_map.clear()
            self.audio_map.clear()
            
            for f in formats:
                if f.get('vcodec') != 'none' and f.get('height'):
                    res = f"{f['height']}p ({f['ext']})"
                    if res not in [x[1] for x in v_list]:
                        v_list.append((f['format_id'], res))
                        self.video_map[res] = f['format_id']
                if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    label = f"{int(f.get('abr', 0))}k ({f['ext']})"
                    if label not in [x[1] for x in a_list]:
                        a_list.append((f['format_id'], label))
                        self.audio_map[label] = f['format_id']
                        
            self.update_queue.put(('formats_ready', 0, (v_list, a_list, info.get('thumbnail'))))
        except Exception:
            self.update_queue.put(('error_header', 0, "Analysis Failed"))

    def handle_start(self):
        url = self.url_entry.get().strip()
        if not url: return
        folder = filedialog.askdirectory()
        if not folder: return
        
        custom_name = self.rename_entry.get().strip()
        v_sel = self.v_qual_var.get()
        a_sel = self.a_qual_var.get()
        
        vid_id = self.video_map.get(v_sel, "bestvideo")
        aud_id = self.audio_map.get(a_sel, "bestaudio")

        self.job_counter += 1
        jid = self.job_counter
        card = DownloadCard(self.scroll_frame, jid, "Initializing...", folder, lambda x: None, self.delete_card)
        card.pack(fill="x", pady=10, padx=10)
        self.cards[jid] = card
        
        self.show_manage()
        threading.Thread(target=self.run_download, args=(jid, url, folder, custom_name, vid_id, aud_id), daemon=True).start()

    def delete_card(self, jid):
        if jid in self.cards:
            self.cards[jid].destroy()
            del self.cards[jid]
            self.sync_history()

    def clear_history(self):
        for jid in list(self.cards.keys()):
            if self.cards[jid].finished:
                self.cards[jid].destroy()
                del self.cards[jid]
        if os.path.exists(HISTORY_FILE): os.remove(HISTORY_FILE)

    def sync_history(self):
        if not self.prefs["keep_history"]: return
        history = []
        for jid, card in self.cards.items():
            if card.finished:
                history.append({"title": card.title_label.cget("text"), "folder": card.folder})
        with open(HISTORY_FILE, "w") as f: json.dump(history, f)

    def load_history(self):
        if not self.prefs["keep_history"] or not os.path.exists(HISTORY_FILE): return
        try:
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)
                for item in history:
                    self.job_counter += 1
                    jid = self.job_counter
                    card = DownloadCard(self.scroll_frame, jid, item["title"], item["folder"], lambda x: None, self.delete_card)
                    card.pack(fill="x", pady=10, padx=10)
                    card.update_progress(1.0, "0", "0")
                    self.cards[jid] = card
        except: pass

    def run_download(self, jid, url, folder, custom_name, vid_id, aud_id):
        try:
            info = self.engine.get_info(url)
            title = custom_name if custom_name else info.get('title', 'Video')
            thumb = info.get('thumbnail')
            extractor = info.get('extractor_key', 'Generic')
            
            self.update_queue.put(('meta_update', jid, (title, thumb, extractor)))
            
            mode, ext = self.mode_var.get(), self.ext_var.get()
            opts = {'outtmpl': os.path.join(folder, f"{title}.%(ext)s")}
            
            if self.prefs["embed_thumb"]:
                opts['writethumbnail'] = True
                opts['postprocessors'] = [{'key': 'EmbedThumbnail'}, {'key': 'FFmpegMetadata'}]

            if mode == "Audio":
                opts['format'] = aud_id
                if 'postprocessors' not in opts: opts['postprocessors'] = []
                opts['postprocessors'].append({'key': 'FFmpegExtractAudio','preferredcodec': ext if ext in ['mp3','wav','m4a'] else 'mp3'})
            elif mode == "Video":
                opts['format'] = vid_id
                if ext != 'mp4': 
                    if 'postprocessors' not in opts: opts['postprocessors'] = []
                    opts['postprocessors'].append({'key': 'FFmpegVideoConvertor', 'preferedformat': ext})
            else:
                opts['format'] = f"{vid_id}+{aud_id}/best"

            def hook(d):
                if d['status'] == 'downloading':
                    p = d.get('downloaded_bytes', 0) / (d.get('total_bytes') or d.get('total_bytes_estimate', 1))
                    self.update_queue.put(('progress', jid, (p, d.get('_speed_str', 'N/A'), d.get('_eta_str', 'N/A'))))
                elif d['status'] == 'finished':
                    self.update_queue.put(('progress', jid, (1.0, "0", "0")))

            self.engine.download(url, opts, hook)
            self.sync_history()
        except Exception as e:
            self.update_queue.put(('error', jid, str(e)))

    def check_queue(self):
        while not self.update_queue.empty():
            m_type, jid, data = self.update_queue.get()
            if m_type == 'formats_ready':
                v_list, a_list, thumb = data
                self.v_qual_menu.configure(values=[x[1] for x in v_list] if v_list else ["Best Video"])
                self.a_qual_menu.configure(values=[x[1] for x in a_list] if a_list else ["Best Audio"])
                self.dl_status_header.configure(text="Analysis Complete ✅", text_color="white")
                self.update_quality_indicator()
            elif m_type == 'meta_update':
                card = self.cards.get(jid)
                if card:
                    card.title_label.configure(text=data[0])
                    if data[1]: threading.Thread(target=card.set_thumbnail, args=(data[1],), daemon=True).start()
                    icon = "📹" if "youtube" in data[2].lower() else "📸" if "instagram" in data[2].lower() else "🌐"
                    card.platform_icon.configure(text=icon)
            elif m_type == 'progress':
                if jid in self.cards: self.cards[jid].update_progress(*data)
            elif m_type == 'error':
                if jid in self.cards: self.cards[jid].update_progress(0, "", "", f"Failed: {data}")
        self.after(100, self.check_queue)

    def update_deps(self):
        if messagebox.askyesno("Update", "Update core engine?"):
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"])
            messagebox.showinfo("Success", "Updated! Please restart.")

if __name__ == "__main__":
    if sys.platform == "win32":
        try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except: pass
    app = VidraApp()
    app.mainloop()
import customtkinter as ctk
import os
import sys
import threading
import json
import shutil
import subprocess
import ctypes
import pyperclip
from tkinter import filedialog, messagebox, simpledialog
from queue import Queue

from src.config import *
from src.engine import DownloadEngine, YdlLogger
from src.ui.components import DownloadCard

class VidraApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME} Pro")
        self.geometry("1100x880")
        
        self.load_prefs()
        self.accent = self.prefs.get("accent_color", ACCENT_COLOR)
        ctk.set_appearance_mode("Light" if self.prefs.get("light_mode") else "Dark")

        self.check_initial_cookies()
        self.engine = DownloadEngine(COOKIE_FILE)
        self.update_queue = Queue()
        self.cards = {}
        self.job_logs = {}
        self.job_counter = 0
        self.drag_data = {"x": 0, "y": 0}
        self.logo_angle = 0
        self.last_clipboard = ""
        
        self.video_map = {}
        self.audio_map = {}

        self.setup_ui()
        self.animate_logo()
        self.check_queue()
        self.load_history()
        self.check_clipboard() # Start clipboard polling loop

    def load_prefs(self):
        defaults = {
            "embed_thumb": True, 
            "keep_history": True, 
            "use_default_path": False, 
            "default_path": "",
            "media_player_path": "",
            "use_media_player": False,
            "dev_mode": False,
            "light_mode": False

        }
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    self.prefs = {**defaults, **json.load(f)}
            except: self.prefs = defaults
        else: self.prefs = defaults

    def save_prefs(self):
        with open(SETTINGS_FILE, "w") as f:
            json.dump(self.prefs, f)

    def check_initial_cookies(self):
        if not os.path.exists(COOKIE_FILE):
            resp = messagebox.askyesno("Missing Cookies", "cookies.txt not found. Would you like to select one now?\n(Required for age-restricted content)")
            if resp:
                self.select_cookie_file()

    def select_cookie_file(self):
        file_path = filedialog.askopenfilename(title="Select cookies.txt", filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if file_path:
            try:
                shutil.copy(file_path, COOKIE_FILE)
                messagebox.showinfo("Success", "Cookies file loaded successfully!")
                self.engine = DownloadEngine(COOKIE_FILE)
                if hasattr(self, 'cookie_status_label'):
                    self.cookie_status_label.configure(text="Status: Found ✅", text_color=self.accent)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load cookies: {e}")

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. SIDEBAR
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=BG_SIDEBAR)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.bind("<ButtonPress-1>", self.start_drag)
        self.sidebar.bind("<B1-Motion>", self.do_drag)
        
        # SASH FOR RESIZING SIDEBAR
        self.sash = ctk.CTkFrame(self, width=4, cursor="sb_h_double_arrow", fg_color=BTN_BG, corner_radius=0)
        self.sash.grid(row=0, column=1, sticky="ns")

        self.sash.bind("<B1-Motion>", self.resize_sidebar)
        
        self.logo_label = ctk.CTkLabel(self.sidebar, text="V", font=("Segoe UI", 48, "bold"), text_color=self.accent)
        self.logo_label.pack(pady=(50, 10))
        
        logo_text = ctk.CTkLabel(self.sidebar, text=APP_NAME, font=("Segoe UI", 24, "bold"), text_color=TEXT_PRIMARY)
        logo_text.pack(pady=(0, 40))

        
        self.create_nav_btn("📥 Downloader", self.show_downloader)
        self.create_nav_btn("📋 Manage", self.show_manage)
        self.create_nav_btn("⚙️ Preferences", self.show_prefs)
        ctk.CTkLabel(self.sidebar, text="", height=1).pack(expand=True)
        self.create_nav_btn("🔄 Update Engine", self.update_deps)
        self.create_nav_btn("❌ Exit", self.destroy)

        # 2. CONTENT AREA
        self.container = ctk.CTkFrame(self, corner_radius=0, fg_color=BG_MAIN)
        self.container.grid(row=0, column=2, sticky="nsew")
        
        # PAGES
        self.page_dl = ctk.CTkFrame(self.container, fg_color="transparent")
        self.setup_downloader_page()
        
        self.page_manage = ctk.CTkFrame(self.container, fg_color="transparent")
        self.setup_manage_page()
        
        self.page_prefs = ctk.CTkScrollableFrame(self.container, fg_color="transparent")
        self.setup_prefs_page()
        
        self.show_downloader()

    def setup_manage_page(self):
        manage_header = ctk.CTkFrame(self.page_manage, fg_color="transparent")
        manage_header.pack(fill="x", pady=(30, 10), padx=40)
        ctk.CTkLabel(manage_header, text="Downloads", font=("Segoe UI", 28, "bold")).pack(side="left")
        
        btn_container = ctk.CTkFrame(manage_header, fg_color="transparent")
        btn_container.pack(side="right")
        
        ctk.CTkButton(btn_container, text="Open Folder", width=100, height=32, corner_radius=16, fg_color="#222222", hover_color="#00CC88", command=self.open_global_folder).pack(side="left", padx=5)
        ctk.CTkButton(btn_container, text="Global Terminal", width=110, height=32, corner_radius=16, fg_color="#222222", hover_color=self.accent, command=self.show_global_logs).pack(side="left", padx=5)
        ctk.CTkButton(btn_container, text="Clear History", width=100, height=32, corner_radius=16, fg_color="#222222", hover_color=DANGER_COLOR, command=self.clear_history).pack(side="left", padx=5)
        
        self.scroll_frame = ctk.CTkScrollableFrame(self.page_manage, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=30, pady=10)

    def setup_downloader_page(self):
        content = ctk.CTkFrame(self.page_dl, fg_color="transparent")
        content.place(relx=0.5, rely=0.48, anchor="center", relwidth=0.9)

        self.dl_status_header = ctk.CTkLabel(content, text="Ready to Download", font=("Segoe UI", 32, "bold"), text_color=TEXT_PRIMARY)
        self.dl_status_header.pack(pady=(20, 5))
        
        self.info_indicator = ctk.CTkLabel(content, text="Waiting for link analysis...", font=("Segoe UI", 13), text_color=self.accent)
        self.info_indicator.pack(pady=(0, 15))
        
        # Link Input Container
        input_container = ctk.CTkFrame(content, height=64, corner_radius=32, fg_color=BG_CARD, border_width=1, border_color=BTN_BG)
        input_container.pack(fill="x", pady=10)
        self.url_entry = ctk.CTkEntry(input_container, placeholder_text="Paste video link...", border_width=0, fg_color="transparent", height=64, font=("Segoe UI", 16), text_color=TEXT_PRIMARY)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=25)

        
        # Extracted analyze_btn as an instance variable we can animate
        self.analyze_btn = ctk.CTkButton(input_container, text="Analyze", width=110, height=40, corner_radius=20, fg_color=self.accent, text_color="black", font=("Segoe UI", 14, "bold"), hover_color="#00CC88", command=self.paste_and_analyze)
        self.analyze_btn.pack(side="right", padx=12)

        sw_frame = ctk.CTkFrame(content, fg_color="transparent")
        sw_frame.pack(fill="x", pady=20)
        self.mode_var = ctk.StringVar(value="Both")
        self.mode_switch = ctk.CTkSegmentedButton(sw_frame, values=["Video", "Audio", "Both"], variable=self.mode_var, height=50, corner_radius=25, fg_color=BG_SIDEBAR, selected_color=self.accent, unselected_color=BG_CARD, command=self.update_ui_state)
        self.mode_switch.pack(side="left", fill="x", expand=True, padx=(0, 15))
        self.ext_var = ctk.StringVar(value="mp4")
        self.ext_menu = ctk.CTkOptionMenu(sw_frame, values=["mp4", "mkv", "webm", "mp3", "m4a"], variable=self.ext_var, fg_color=BG_CARD, button_color=BTN_BG, width=120, height=50, corner_radius=15)
        self.ext_menu.pack(side="right")


        self.quality_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.quality_frame.pack(fill="x", pady=5)
        self.v_qual_var = ctk.StringVar(value="Best Video")
        self.v_qual_menu = ctk.CTkOptionMenu(self.quality_frame, values=["Best Video"], variable=self.v_qual_var, fg_color=BG_CARD, button_color=BTN_BG, height=48, corner_radius=15, command=lambda _: self.update_info_indicator())
        self.v_qual_menu.pack(side="left", fill="x", expand=True, padx=(0, 7))
        self.a_qual_var = ctk.StringVar(value="Best Audio")
        self.a_qual_menu = ctk.CTkOptionMenu(self.quality_frame, values=["Best Audio"], variable=self.a_qual_var, fg_color=BG_CARD, button_color=BTN_BG, height=48, corner_radius=15, command=lambda _: self.update_info_indicator())
        self.a_qual_menu.pack(side="right", fill="x", expand=True, padx=(7, 0))

        self.rename_entry = ctk.CTkEntry(content, placeholder_text="Custom filename (Optional)", height=54, corner_radius=15, fg_color=BG_CARD, border_width=0, font=("Segoe UI", 14), text_color=TEXT_PRIMARY)
        self.rename_entry.pack(fill="x", pady=20)


        self.dl_btn = ctk.CTkButton(content, text="DOWNLOAD", height=60, width=320, corner_radius=30, font=("Segoe UI", 18, "bold"), fg_color=DANGER_COLOR, hover_color="#E03A3A", command=self.handle_start)
        self.dl_btn.pack(pady=10)

    def setup_prefs_page(self):
        ctk.CTkLabel(self.page_prefs, text="Preferences", font=("Segoe UI", 28, "bold")).pack(pady=(30, 20), padx=40, anchor="w")
        container = ctk.CTkFrame(self.page_prefs, fg_color=BG_CARD, corner_radius=20)
        container.pack(fill="x", padx=40, pady=10)

        self.check_thumb = ctk.CTkCheckBox(container, text="Embed Thumbnails into Downloaded Files", font=("Segoe UI", 14), fg_color=self.accent, hover_color="#00CC88", command=self.update_pref_vars)
        if self.prefs["embed_thumb"]: self.check_thumb.select()
        self.check_thumb.pack(anchor="w", padx=30, pady=15)

        self.check_history = ctk.CTkCheckBox(container, text="Keep Download History Persistent", font=("Segoe UI", 14), fg_color=self.accent, hover_color="#00CC88", command=self.update_pref_vars)
        if self.prefs["keep_history"]: self.check_history.select()
        self.check_history.pack(anchor="w", padx=30, pady=15)

        self.check_default_path = ctk.CTkCheckBox(container, text="Default download location persistent", font=("Segoe UI", 14), fg_color=self.accent, hover_color="#00CC88", command=self.update_pref_vars)
        if self.prefs["use_default_path"]: self.check_default_path.select()
        self.check_default_path.pack(anchor="w", padx=30, pady=(15, 5))

        self.path_label = ctk.CTkLabel(container, text=f"Path: {self.prefs.get('default_path', 'Not set')}", font=("Segoe UI", 11), text_color="#888888")
        self.path_label.pack(anchor="w", padx=60, pady=(0, 5))
        ctk.CTkButton(container, text="Change Path", width=100, height=24, corner_radius=12, fg_color="#333333", hover_color="#444444", command=self.set_default_directory).pack(anchor="w", padx=60, pady=(0, 15))

        self.check_player = ctk.CTkCheckBox(container, text="Use Custom Media Player", font=("Segoe UI", 14), fg_color=self.accent, hover_color="#00CC88", command=self.update_pref_vars)
        if self.prefs["use_media_player"]: self.check_player.select()
        self.check_player.pack(anchor="w", padx=30, pady=(15, 5))
        
        self.player_path_label = ctk.CTkLabel(container, text=f"Player: {self.prefs.get('media_player_path', 'System Default')}", font=("Segoe UI", 11), text_color="#888888")
        self.player_path_label.pack(anchor="w", padx=60, pady=(0, 5))
        ctk.CTkButton(container, text="Select Player Executable", width=150, height=24, corner_radius=12, fg_color="#333333", hover_color="#444444", command=self.set_media_player).pack(anchor="w", padx=60, pady=(0, 15))

        ctk.CTkLabel(container, text="Cookie Settings", font=("Segoe UI", 14), text_color=TEXT_PRIMARY).pack(anchor="w", padx=30, pady=(15, 5))
        cookie_exists = os.path.exists(COOKIE_FILE)
        self.cookie_status_label = ctk.CTkLabel(container, text=f"Status: {'Found ✅' if cookie_exists else 'Not Found ❌'}", font=("Segoe UI", 11), text_color=self.accent if cookie_exists else DANGER_COLOR)
        self.cookie_status_label.pack(anchor="w", padx=60, pady=(0, 5))
        ctk.CTkButton(container, text="Select Cookie File", width=150, height=24, corner_radius=12, fg_color="#333333", hover_color="#444444", command=self.select_cookie_file).pack(anchor="w", padx=60, pady=(0, 15))

        self.check_dev = ctk.CTkCheckBox(container, text="Developer Mode (Show technical IDs and Sizes)", font=("Segoe UI", 14), fg_color=self.accent, hover_color="#00CC88", command=self.toggle_dev_mode)
        if self.prefs["dev_mode"]: self.check_dev.select()
        self.check_dev.pack(anchor="w", padx=30, pady=(15, 5))
        
        self.check_light = ctk.CTkCheckBox(container, text="Light Mode / Dark Mode", font=("Segoe UI", 14), fg_color=self.accent, hover_color="#00CC88", command=self.toggle_theme)
        if self.prefs.get("light_mode"): self.check_light.select()
        self.check_light.pack(anchor="w", padx=30, pady=(15, 20))

        # ACCENT OPTIONS
        ctk.CTkLabel(container, text="Theme Accent Color", font=("Segoe UI", 14), text_color=TEXT_PRIMARY).pack(anchor="w", padx=30, pady=(15, 5))
        color_frame = ctk.CTkFrame(container, fg_color="transparent")
        color_frame.pack(anchor="w", padx=60, pady=(0, 15))
        
        ctk.CTkButton(color_frame, text="Custom...", width=100, height=32, corner_radius=16, fg_color=self.accent, text_color="black", hover_color=BTN_HOVER, command=self.choose_accent_color).pack(side="left", padx=(0, 10))
        ctk.CTkButton(color_frame, text="Win Theme", width=100, height=32, corner_radius=16, fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_PRIMARY, command=self.get_windows_accent).pack(side="left", padx=(0, 10))
        ctk.CTkButton(color_frame, text="Reset", width=80, height=32, corner_radius=16, fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_PRIMARY, command=self.reset_accent).pack(side="left")

    # --- ACTIONS & LOGIC ---
    
    def resize_sidebar(self, event):
        # Calculate new width based on mouse X (relative to window root X)
        new_width = self.winfo_pointerx() - self.winfo_rootx()
        if new_width < 150: new_width = 150
        if new_width > 600: new_width = 600
        self.sidebar.configure(width=new_width)
        # Setting grid column minsize prevents jitter/snapback when letting go of mouse
        self.grid_columnconfigure(0, minsize=new_width)


    def toggle_theme(self):
        is_light = bool(self.check_light.get())
        ctk.set_appearance_mode("Light" if is_light else "Dark")
        self.prefs["light_mode"] = is_light
        self.save_prefs()
        
    def open_global_folder(self):
        path = self.prefs.get("default_path")
        if path and os.path.exists(path):
            os.startfile(path)
        else:
            messagebox.showinfo("Info", "Default download path is not set or doesn't exist. Please set it in Preferences.")
    
    def choose_accent_color(self):
        from tkinter import colorchooser
        color = colorchooser.askcolor(title="Choose Accent Color", color=self.accent)
        if color and color[1]:
            self.prefs["accent_color"] = color[1]
            self.save_prefs()
            messagebox.showinfo("Restart Required", "Accent color saved. Please restart Vidra to fully apply the changes.")

    def get_windows_accent(self):
        try:
            import winreg
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(registry, r'Software\Microsoft\Windows\DWM')
            value, _ = winreg.QueryValueEx(key, 'ColorizationColor')
            hex_color = f"#{value & 0xFFFFFF:06x}"
            self.prefs["accent_color"] = hex_color
            self.save_prefs()
            messagebox.showinfo("Restart Required", f"Windows accent ({hex_color}) saved. Please restart Vidra to apply.")
        except Exception as e:
            messagebox.showerror("Error", "Could not fetch Windows accent color.")

    def reset_accent(self):
        if "accent_color" in self.prefs:
            del self.prefs["accent_color"]
        self.save_prefs()
        messagebox.showinfo("Restart Required", "Accent color reset. Please restart Vidra to apply.")

    def check_clipboard(self):
        try:
            current_clipboard = pyperclip.paste().strip()
            # Detect YouTube or Instagram links
            domains = ["youtube.com", "youtu.be", "instagram.com", "tiktok.com", "twitter.com", "x.com"]
            if current_clipboard != self.last_clipboard and current_clipboard.startswith("http"):
                self.last_clipboard = current_clipboard
                domain = current_clipboard.lower()
                
                if any(d in domain for d in domains):
                    # Auto paste into the UI and flash the box
                    self.url_entry.delete(0, 'end')
                    self.url_entry.insert(0, current_clipboard)
                    
                    if self.page_dl.winfo_ismapped():
                        self.animate_analyze_btn(6) # Pulse animation 3 full cycles
        except: pass
        self.after(1000, self.check_clipboard)

    def animate_analyze_btn(self, count):
        if count <= 0:
            self.analyze_btn.configure(fg_color=self.accent, text_color="black")
            return
        
        current_color = self.analyze_btn.cget("fg_color")
        new_color = "#FFFFFF" if current_color == self.accent else self.accent
        txt_color = "black" if new_color == self.accent else "#000000"
        
        self.analyze_btn.configure(fg_color=new_color, text_color=txt_color)
        self.after(200, lambda: self.animate_analyze_btn(count - 1))

    def toggle_dev_mode(self):
        if not self.prefs["dev_mode"]:
            pwd = simpledialog.askstring("Developer Mode", "Enter password:", show='*')
            if pwd == "1117":
                self.prefs["dev_mode"] = True
                messagebox.showinfo("Dev Mode", "Developer mode enabled.")
            else:
                self.check_dev.deselect()
                messagebox.showerror("Error", "Incorrect password.")
        else:
            self.prefs["dev_mode"] = False
            messagebox.showinfo("Dev Mode", "Developer mode disabled.")
        self.save_prefs()

    def set_media_player(self):
        path = filedialog.askopenfilename(title="Select Media Player Executable", filetypes=[("Executable", "*.exe"), ("All files", "*.*")])
        if path:
            self.prefs["media_player_path"] = path
            self.player_path_label.configure(text=f"Player: {path}")
            self.save_prefs()

    def set_default_directory(self):
        path = filedialog.askdirectory()
        if path:
            self.prefs["default_path"] = path
            self.path_label.configure(text=f"Path: {path}")
            self.save_prefs()

    def update_pref_vars(self):
        self.prefs["embed_thumb"] = bool(self.check_thumb.get())
        self.prefs["keep_history"] = bool(self.check_history.get())
        self.prefs["use_default_path"] = bool(self.check_default_path.get())
        self.prefs["use_media_player"] = bool(self.check_player.get())
        self.save_prefs()

    def format_size(self, size_bytes):
        if not size_bytes or size_bytes <= 0: return ""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024: return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def update_info_indicator(self):
        mode = self.mode_var.get()
        v_sel, a_sel = self.v_qual_var.get(), self.a_qual_var.get()
        v_info = self.video_map.get(v_sel, {})
        a_info = self.audio_map.get(a_sel, {})
        v_size, a_size = v_info.get('size', 0), a_info.get('size', 0)
        
        total = 0
        txt = f"Selection: {v_sel if mode != 'Audio' else ''} "
        if mode == "Video": total = v_size
        elif mode == "Audio": total = a_size; txt = f"Selection: {a_sel} "
        else: total = v_size + a_size; txt += f"+ {a_sel} "
            
        sz = self.format_size(total)
        txt += f"| Est. Size: {sz if sz else '?'}"
        self.info_indicator.configure(text=txt)

    def animate_logo(self):
        colors = ["#00FFAA", "#00E099", "#00CC88", "#00B277"]
        idx = int((self.logo_angle / 10) % len(colors))
        self.logo_label.configure(text_color=colors[idx])
        self.logo_angle += 1
        self.after(100, self.animate_logo)

    def start_drag(self, event):
        self.drag_data["x"] = event.x; self.drag_data["y"] = event.y

    def do_drag(self, event):
        x = self.winfo_x() + (event.x - self.drag_data["x"])
        y = self.winfo_y() + (event.y - self.drag_data["y"])
        self.geometry(f"+{x}+{y}")

    def create_nav_btn(self, text, command):
        btn = ctk.CTkButton(self.sidebar, text=text, font=("Segoe UI", 14), anchor="w", fg_color="transparent", hover_color=BTN_HOVER, height=50, corner_radius=10, command=command, text_color=TEXT_PRIMARY)
        btn.pack(fill="x", padx=15, pady=5)
        return btn


    def show_downloader(self):
        self.page_manage.pack_forget(); self.page_prefs.pack_forget()
        self.page_dl.pack(fill="both", expand=True)

    def show_manage(self):
        self.page_dl.pack_forget(); self.page_prefs.pack_forget()
        self.page_manage.pack(fill="both", expand=True)

    def show_prefs(self):
        self.page_dl.pack_forget(); self.page_manage.pack_forget()
        self.page_prefs.pack(fill="both", expand=True)

    def update_ui_state(self, choice):
        if choice == "Audio": self.v_qual_menu.configure(state="disabled"); self.a_qual_menu.configure(state="normal")
        elif choice == "Video": self.v_qual_menu.configure(state="normal"); self.a_qual_menu.configure(state="disabled")
        else: self.v_qual_menu.configure(state="normal"); self.a_qual_menu.configure(state="normal")
        self.update_info_indicator()

    def paste_and_analyze(self):
        url = self.url_entry.get().strip()
        if not url: return
        self.dl_status_header.configure(text="Analyzing Link... 🔍", text_color=self.accent)
        self.job_logs[-1] = ["[START] Fetching metadata for analysis..."]
        threading.Thread(target=self.run_fetch, args=(url,), daemon=True).start()

    def run_fetch(self, url):
        try:
            logger = YdlLogger(self.update_queue, -1)
            info = self.engine.get_info(url, logger=logger)
            formats = info.get('formats', [])
            v_list, a_list = [], []
            temp_v_map, temp_a_map = {} , {}
            is_dev = self.prefs.get("dev_mode", False)
            
            for f in formats:
                fid = str(f.get('format_id', 'N/A'))
                ext = f.get('ext', '???')
                height = f.get('height')
                abr = f.get('abr')
                filesize = f.get('filesize') or f.get('filesize_approx')
                
                f_size_str = f"({self.format_size(filesize)})" if filesize else ""
                v_codec = str(f.get('vcodec') or 'none').lower()
                a_codec = str(f.get('acodec') or 'none').lower()
                
                display_label = ""
                if v_codec != 'none' and a_codec == 'none':
                    display_label = f"{height}p {ext}" if height else f"Video {ext}"
                elif a_codec != 'none' and v_codec == 'none':
                    display_label = f"Audio {ext} ({abr}k)" if abr else f"Audio {ext}"
                elif v_codec != 'none' and a_codec != 'none':
                    display_label = f"{height}p {ext}" if height else f"Combined {ext}"
                
                if is_dev: final_label = f"{display_label} ({fid}) {f_size_str}".strip()
                else: final_label = f"{display_label}".strip()
                
                if not final_label: continue

                if v_codec != 'none':
                    if final_label not in [x[1] for x in v_list]:
                        v_list.append((fid, final_label, height or 0))
                        temp_v_map[final_label] = {'id': fid, 'size': filesize or 0}
                        
                if a_codec != 'none':
                    if v_codec == 'none' or is_dev:
                        if final_label not in [x[1] for x in a_list]:
                            a_list.append((fid, final_label, abr or 0))
                            temp_a_map[final_label] = {'id': fid, 'size': filesize or 0}
            
            v_list.sort(key=lambda x: x[2], reverse=True)
            a_list.sort(key=lambda x: x[2], reverse=True)
            
            self.update_queue.put(('formats_ready', 0, (
                [(x[0], x[1]) for x in v_list], 
                [(x[0], x[1]) for x in a_list], 
                info.get('thumbnail'), temp_v_map, temp_a_map
            )))
        except Exception as e:
            self.update_queue.put(('error_header', 0, f"Analysis Failed: {str(e)[:50]}"))

    def handle_start(self):
        url = self.url_entry.get().strip()
        if not url: return
        folder = self.prefs["default_path"] if self.prefs.get("use_default_path") else filedialog.askdirectory()
        if not folder: return
        
        v_sel, a_sel = self.v_qual_var.get(), self.a_qual_var.get()
        vid_info = self.video_map.get(v_sel, {'id': 'bestvideo', 'size': 0})
        aud_info = self.audio_map.get(a_sel, {'id': 'bestaudio', 'size': 0})

        self.job_counter += 1
        jid = self.job_counter; self.job_logs[jid] = []
        card = DownloadCard(self.scroll_frame, jid, "Initializing...", folder, lambda x: None, self.delete_card, self.show_job_log, self.play_video, accent_color=self.accent)
        card.pack(fill="x", pady=10, padx=10); self.cards[jid] = card
        self.show_manage()
        threading.Thread(target=self.run_download, args=(jid, url, folder, self.rename_entry.get().strip(), vid_info['id'], aud_info['id']), daemon=True).start()

    def show_job_log(self, jid):
        log_win = ctk.CTkToplevel(self); log_win.title(f"Terminal Log - Job #{jid}"); log_win.geometry("700x500")
        txt = ctk.CTkTextbox(log_win, font=("Consolas", 12)); txt.pack(fill="both", expand=True, padx=10, pady=10)
        txt.insert("0.0", "\n".join(self.job_logs.get(jid, ["No logs available."]))); txt.configure(state="disabled")

    def show_global_logs(self):
        all_logs = []
        for jid, logs in sorted(self.job_logs.items()):
            all_logs.append(f"--- {'ANALYSIS PHASE' if jid == -1 else f'JOB #{jid}'} ---")
            all_logs.extend(logs); all_logs.append("\n")
        log_win = ctk.CTkToplevel(self); log_win.title("Global Download Terminal"); log_win.geometry("800x600")
        txt = ctk.CTkTextbox(log_win, font=("Consolas", 12)); txt.pack(fill="both", expand=True, padx=10, pady=10)
        txt.insert("0.0", "\n".join(all_logs))

    def play_video(self, file_path):
        if not file_path or not os.path.exists(file_path): messagebox.showerror("Error", "File not found."); return
        player = self.prefs.get("media_player_path")
        if self.prefs.get("use_media_player") and player and os.path.exists(player):
            subprocess.Popen([player, file_path])
        else: os.startfile(file_path)

    def delete_card(self, jid):
        if jid in self.cards: self.cards[jid].destroy(); del self.cards[jid]; self.sync_history()

    def clear_history(self):
        for jid in list(self.cards.keys()):
            if self.cards[jid].finished: self.cards[jid].destroy(); del self.cards[jid]
        if os.path.exists(HISTORY_FILE): os.remove(HISTORY_FILE)

    def sync_history(self):
        if not self.prefs["keep_history"]: return
        history = [{"title": c.title, "folder": c.folder, "file_path": c.file_path} for c in self.cards.values() if c.finished]
        with open(HISTORY_FILE, "w") as f: json.dump(history, f)

    def load_history(self):
        if not self.prefs["keep_history"] or not os.path.exists(HISTORY_FILE): return
        try:
            with open(HISTORY_FILE, "r") as f:
                for item in json.load(f):
                    self.job_counter += 1; jid = self.job_counter
                    card = DownloadCard(self.scroll_frame, jid, item["title"], item["folder"], lambda x: None, self.delete_card, self.show_job_log, self.play_video, accent_color=self.accent)
                    card.file_path = item.get("file_path", ""); card.pack(fill="x", pady=10, padx=10)
                    card.update_progress(1.0, "0", "0", size_text="Archived"); self.cards[jid] = card
        except: pass

    def run_download(self, jid, url, folder, custom_name, vid_id, aud_id):
        try:
            info = self.engine.get_info(url)
            title = custom_name if custom_name else info.get('title', 'Video')
            self.update_queue.put(('meta_update', jid, (title, info.get('thumbnail'), info.get('extractor_key', 'Generic'))))
            opts = {'outtmpl': os.path.join(folder, f"{title}.%(ext)s")}
            if self.prefs["embed_thumb"]: opts['writethumbnail'] = True; opts['postprocessors'] = [{'key': 'EmbedThumbnail'}, {'key': 'FFmpegMetadata'}]
            
            mode = self.mode_var.get(); ext = self.ext_var.get()
            if mode == "Audio":
                opts['format'] = aud_id
                if 'postprocessors' not in opts: opts['postprocessors'] = []
                opts['postprocessors'].append({'key': 'FFmpegExtractAudio','preferredcodec': ext if ext in ['mp3','wav','m4a'] else 'mp3'})
            elif mode == "Video":
                opts['format'] = f"{vid_id}+bestaudio/best"
                if ext != 'mp4': 
                    if 'postprocessors' not in opts: opts['postprocessors'] = []
                    opts['postprocessors'].append({'key': 'FFmpegVideoConvertor', 'preferedformat': ext})
            else:
                opts['format'] = f"{vid_id}+{aud_id}/best"
            
            def hook(d):
                if d['status'] == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 1)
                    self.update_queue.put(('progress', jid, (d.get('downloaded_bytes', 0)/total, d.get('_speed_str', 'N/A'), d.get('_eta_str', 'N/A'), None, self.format_size(total))))
                elif d['status'] == 'finished':
                    self.update_queue.put(('progress', jid, (1.0, "0", "0", None, "Processing...")))
                    self.update_queue.put(('file_done', jid, d.get('filename')))

            self.engine.download(url, opts, hook, YdlLogger(self.update_queue, jid)); self.sync_history()
        except Exception as e: self.update_queue.put(('error', jid, str(e)))

    def check_queue(self):
        while not self.update_queue.empty():
            msg = self.update_queue.get()
            if not msg: continue
            m_type, jid, data = msg
            
            if m_type == 'formats_ready':
                v_list, a_list, thumb, v_map, a_map = data
                self.video_map = v_map
                self.audio_map = a_map
                self.v_qual_menu.configure(values=[x[1] for x in v_list] if v_list else ["Best Video"])
                self.a_qual_menu.configure(values=[x[1] for x in a_list] if a_list else ["Best Audio"])
                self.dl_status_header.configure(text="Analysis Complete ✅", text_color=TEXT_PRIMARY)
                self.update_info_indicator()
            elif m_type == 'error_header':
                self.dl_status_header.configure(text=data, text_color=DANGER_COLOR)
            elif m_type == 'meta_update':
                card = self.cards.get(jid)
                if card:
                    # FIX HISTORY BUG: we now store the analyzed title in the card instance so 'sync_history' saves the real name
                    card.title = data[0]
                    card.title_label.configure(text=data[0][:60] + ("..." if len(data[0]) > 60 else ""))
                    if data[1]: threading.Thread(target=card.set_thumbnail, args=(data[1],), daemon=True).start()
                    icon = "📹" if "youtube" in data[2].lower() else "📸" if "instagram" in data[2].lower() else "🌐"
                    card.platform_icon.configure(text=icon)
            elif m_type == 'log':
                if jid not in self.job_logs: self.job_logs[jid] = []
                self.job_logs[jid].append(data)
            elif m_type == 'progress':
                if jid in self.cards: self.cards[jid].update_progress(*data)
            elif m_type == 'file_done':
                if jid in self.cards: self.cards[jid].file_path = data
            elif m_type == 'error':
                if jid in self.cards: self.cards[jid].update_progress(0, "", "", f"Failed: {data}")
        self.after(100, self.check_queue)

    def update_deps(self):
        if messagebox.askyesno("Update", "Update core engine?"):
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"])
            messagebox.showinfo("Success", "Updated! Please restart.")

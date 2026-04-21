import os
import customtkinter as ctk
import requests
from io import BytesIO
from PIL import Image
from src.config import BG_CARD, ACCENT_COLOR, DANGER_COLOR, BTN_BG, BTN_HOVER, TEXT_PRIMARY, TEXT_MUTED

class DownloadCard(ctk.CTkFrame):

    def __init__(self, master, job_id, title, folder, stop_callback, delete_callback, terminal_callback, play_callback, **kwargs):
        # Increased corner radius and added subtle border for more One UI aesthetic
        super().__init__(master, fg_color=BG_CARD, corner_radius=20, border_width=1, border_color="#2A2A2A", **kwargs)
        self.job_id = job_id
        self.folder = folder
        self.title = title
        self.stop_callback = stop_callback
        self.delete_callback = delete_callback
        self.terminal_callback = terminal_callback
        self.play_callback = play_callback
        self.finished = False
        self.file_path = ""
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)
        
        # Larger thumbnail placeholder for better visual balance
        self.thumb_label = ctk.CTkLabel(self, text="", width=140, height=80, fg_color=BTN_BG, corner_radius=15)
        self.thumb_label.grid(row=0, column=0, rowspan=3, padx=20, pady=20)
        
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=1, sticky="ew", pady=(20, 5))
        
        self.platform_icon = ctk.CTkLabel(header_frame, text="🌐", font=("Segoe UI", 16))
        self.platform_icon.pack(side="left", padx=(0, 10))
        
        display_title = (title[:60] + '...') if len(title) > 60 else title
        self.title_label = ctk.CTkLabel(header_frame, text=display_title, font=("Segoe UI", 16, "bold"), anchor="w", text_color=TEXT_PRIMARY)
        self.title_label.pack(side="left", fill="x")

        
        # Thicker progress bar to match One UI components
        self.p_bar = ctk.CTkProgressBar(self, height=10, progress_color=self.accent_color, fg_color="#333333")
        self.p_bar.grid(row=1, column=1, sticky="w", padx=(0, 20), pady=0)

        self.p_bar.set(0)
        
        self.stats_label = ctk.CTkLabel(self, text="Waiting...", font=("Segoe UI", 12), text_color=TEXT_MUTED)
        self.stats_label.grid(row=2, column=1, sticky="w", pady=(0, 20))

        # Action Buttons container with adjusted padding
        self.actions = ctk.CTkFrame(self, fg_color="transparent")
        self.actions.grid(row=0, column=2, rowspan=3, padx=20)
        
        self.folder_btn = ctk.CTkButton(self.actions, text="📁", width=40, height=40, corner_radius=12, fg_color=BTN_BG, hover_color=BTN_HOVER, command=self.open_folder)
        self.folder_btn.pack(side="left", padx=3)
        
        self.term_btn = ctk.CTkButton(self.actions, text="💻", width=40, height=40, corner_radius=12, fg_color=BTN_BG, hover_color=BTN_HOVER, command=lambda: self.terminal_callback(self.job_id))
        self.term_btn.pack(side="left", padx=3)
        
        self.action_btn = ctk.CTkButton(self.actions, text="🛑", width=40, height=40, corner_radius=12, fg_color="#6A2222", hover_color=DANGER_COLOR, command=self.handle_action)
        self.action_btn.pack(side="left", padx=3)

    def set_thumbnail(self, url):
        try:
            response = requests.get(url, timeout=5)
            img_data = BytesIO(response.content)
            img = Image.open(img_data)
            # Re-scale thumbnail to fit the new larger slot (140x80)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(140, 80))
            self.thumb_label.configure(image=ctk_img, text="")
        except:
            self.thumb_label.configure(text="No Preview")

    def update_progress(self, progress, speed, eta, status_text=None, size_text=""):
        self.p_bar.set(progress)
        if status_text:
            self.stats_label.configure(text=status_text)
        else:
            self.stats_label.configure(text=f"{size_text} • Speed: {speed} • ETA: {eta}")
        
        if progress >= 1 and not self.finished:
            self.finished = True
            self.stats_label.configure(text=f"Finished ({size_text})", text_color=self.accent_color)
            self.action_btn.configure(text="🗑️", fg_color=BTN_BG, hover_color=DANGER_COLOR)

            
            # Hide old buttons to make room for play button for cleaner One UI grid
            for w in self.actions.winfo_children(): w.pack_forget()
            
            self.folder_btn.pack(side="left", padx=3)
            self.term_btn.pack(side="left", padx=3)
            self.play_btn = ctk.CTkButton(self.actions, text="▶️", width=40, height=40, corner_radius=12, fg_color=self.accent_color, text_color="black", hover_color="#00CC88", command=self.play_file)
            self.play_btn.pack(side="left", padx=3)
            self.action_btn.pack(side="left", padx=3)

    def open_folder(self):
        if os.path.exists(self.folder):
            os.startfile(self.folder)

    def play_file(self):
        self.play_callback(self.file_path)

    def handle_action(self):
        if self.finished:
            self.delete_callback(self.job_id)
        else:
            self.stop_callback(self.job_id)
            self.stats_label.configure(text="Stopped", text_color=DANGER_COLOR)

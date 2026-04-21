import os

class YdlLogger:
    def __init__(self, queue, job_id):
        self.queue = queue
        self.job_id = job_id

    def debug(self, msg):
        if msg.startswith('post-process'): return
        self.queue.put(('log', self.job_id, f"[DEBUG] {msg}"))

    def warning(self, msg):
        self.queue.put(('log', self.job_id, f"[WARNING] {msg}"))

    def error(self, msg):
        self.queue.put(('log', self.job_id, f"[ERROR] {msg}"))

class DownloadEngine:
    def __init__(self, cookie_path):
        import yt_dlp
        self.cookie_path = cookie_path
        self.common_opts = {
            'quiet': True,
            'no_warnings': False,
            'cookiefile': os.path.abspath(self.cookie_path) if os.path.exists(self.cookie_path) else None,
            'noplaylist': True,
            'verbose': False,
            'nocheckcertificate': True,
        }

    def get_info(self, url, logger=None):
        import yt_dlp
        opts = {**self.common_opts}
        opts['check_formats'] = False 
        if logger: opts['logger'] = logger
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    def download(self, url, opts, progress_hook, logger):
        import yt_dlp
        final_opts = {**self.common_opts, **opts}
        if 'mp4' in str(final_opts.get('outtmpl', '')):
            final_opts['merge_output_format'] = 'mp4'
        
        final_opts['progress_hooks'] = [progress_hook]
        final_opts['logger'] = logger
        with yt_dlp.YoutubeDL(final_opts) as ydl:
            ydl.download([url])

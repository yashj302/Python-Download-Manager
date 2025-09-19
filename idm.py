import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk  # <-- Add this import
import requests
import threading
import os
import time

def format_bytes(size):
    if size < 1024:
        return f"{size} B"
    elif size < 1024 ** 2:
        return f"{size / 1024:.2f} KB"
    elif size < 1024 ** 3:
        return f"{size / (1024 ** 2):.2f} MB"
    else:
        return f"{size / (1024 ** 3):.2f} GB"

def download_chunk(url, start_byte, end_byte, part_num, file_path, progress_callback):
    try:
        headers = {'Range': f'bytes={start_byte}-{end_byte}'}
        response = requests.get(url, headers=headers, stream=True, timeout=20)
        response.raise_for_status()
        part_filename = f"{file_path}.part{part_num}"
        with open(part_filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    progress_callback(len(chunk))
        return part_filename
    except requests.exceptions.RequestException:
        return None

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x, y, _, cy = self.widget.bbox("insert") if hasattr(self.widget, "bbox") else (0, 0, 0, 0)
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() + 25
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, background="#ffffe0", relief="solid", borderwidth=1, font=("Segoe UI", 9))
        label.pack(ipadx=5, ipady=2)

    def hide_tip(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()


# ...existing code...

class DownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Download Manager Pro")
        self.root.geometry("540x470")
        self.root.resizable(False, False)
        self.cancel_event = threading.Event()  # <-- Add this
        self.pause_event = threading.Event()  # <-- Add this

        # Use a modern theme
        self.root.configure(bg="#23272f")
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background="#23272f")
        style.configure("TLabel", background="#23272f", foreground="#e4e7ec", font=("Segoe UI", 11))
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"), background="#23272f", foreground="#fff")
        style.configure("Stats.TLabelframe", background="#23272f", foreground="#fff", borderwidth=0)
        style.configure("Stats.TLabelframe.Label", font=("Segoe UI", 13, "bold"), background="#23272f", foreground="#fff")
        style.configure("TEntry", fieldbackground="#23272f", foreground="#fff", borderwidth=0, font=("Segoe UI", 11))
        style.configure("Blue.TProgressbar", troughcolor="#23272f", background="#2e90fa", bordercolor="#23272f", thickness=16)
        style.layout("Blue.TProgressbar",[('Horizontal.Progressbar.trough',
            {'children': [('Horizontal.Progressbar.pbar',
                            {'side': 'left', 'sticky': 'ns'})],
            'sticky': 'nswe'})])
        style.configure("Download.TButton", font=("Segoe UI", 12, "bold"), foreground="#fff", background="#2e90fa", borderwidth=0)
        style.map("Download.TButton",
                  background=[("active", "#175cd3"), ("disabled", "#6c757d")])
        style.configure("Pause.TButton", font=("Segoe UI", 12, "bold"), foreground="#23272f", background="#e4e7ec", borderwidth=0)
        style.map("Pause.TButton",
                  background=[("active", "#cdd0d4"), ("disabled", "#6c757d")])
        style.configure("Cancel.TButton", font=("Segoe UI", 12, "bold"), foreground="#fff", background="#d92d20", borderwidth=0)
        style.map("Cancel.TButton",
                  background=[("active", "#b42318"), ("disabled", "#6c757d")])

        # --- Main Frame ---
        self.main_frame = ttk.Frame(root, style="TFrame")
        self.main_frame.pack(fill='both', expand=True, padx=16, pady=16)

        # --- Title ---
        self.title_label = ttk.Label(self.main_frame, text="Python Download Manager Pro", style="Title.TLabel", anchor="center")
        self.title_label.pack(pady=(0, 12), fill='x')

        # --- URL Entry ---
        self.url_frame = ttk.Frame(self.main_frame, style="TFrame")
        self.url_frame.pack(fill='x', pady=(0, 12))
        self.url_label = ttk.Label(self.url_frame, text="File URL:", style="TLabel")
        self.url_label.pack(side='left', padx=(0, 10))
        self.url_entry = ttk.Entry(self.url_frame, width=50, font=("Segoe UI", 11))
        self.url_entry.pack(side='left', fill='x', expand=True)
        self.url_entry.insert(0, "https://install.avcdn.net/avg/iavs9x/avg_antivirus_free_setup_offline.exe")

        # --- Button Row ---
        self.button_frame = ttk.Frame(self.main_frame, style="TFrame")
        self.button_frame.pack(fill='x', pady=(0, 12))
        self.download_button = ttk.Button(self.button_frame, text="⬇ Download", style="Download.TButton", command=self.start_download_thread)
        self.download_button.pack(side='left', fill='x', expand=True, ipadx=10, ipady=6)
        self.pause_button = ttk.Button(self.button_frame, text="Pause Ⅱ", style="Pause.TButton", command=self.toggle_pause, state="disabled")
        self.pause_button.pack(side='left', fill='x', expand=True, padx=10, ipadx=10, ipady=6)
        self.cancel_button = ttk.Button(self.button_frame, text="Cancel  ✖", style="Cancel.TButton", command=self.cancel_download, state="disabled")
        self.cancel_button.pack(side='left', fill='x', expand=True, ipadx=10, ipady=6)

        # --- Separator ---
        ttk.Separator(self.main_frame, orient='horizontal').pack(fill='x', pady=(0, 16))

        # --- Stats Frame ---
        self.stats_frame = ttk.Labelframe(self.main_frame, text="Download Stats", style="Stats.TLabelframe", padding="16")
        self.stats_frame.pack(fill='x', pady=(0, 8))

        self.size_label = ttk.Label(self.stats_frame, text="Total Size:", style="TLabel")
        self.size_label.grid(row=0, column=0, sticky='w', padx=(0, 8), pady=2)
        self.size_val_label = ttk.Label(self.stats_frame, text="0 MB", style="TLabel")
        self.size_val_label.grid(row=0, column=1, sticky='w', pady=2)

        self.downloaded_label = ttk.Label(self.stats_frame, text="Downloaded:", style="TLabel")
        self.downloaded_label.grid(row=1, column=0, sticky='w', padx=(0, 8), pady=2)
        self.downloaded_val_label = ttk.Label(self.stats_frame, text="0 MB", style="TLabel")
        self.downloaded_val_label.grid(row=1, column=1, sticky='w', pady=2)

        self.speed_label = ttk.Label(self.stats_frame, text="Speed:", style="TLabel")
        self.speed_label.grid(row=2, column=0, sticky='w', padx=(0, 8), pady=2)
        self.speed_val_label = ttk.Label(self.stats_frame, text="0 KB/s", style="TLabel")
        self.speed_val_label.grid(row=2, column=1, sticky='w', pady=2)

        self.time_label = ttk.Label(self.stats_frame, text="Total Time:", style="TLabel")
        self.time_label.grid(row=3, column=0, sticky='w', padx=(0, 8), pady=2)
        self.time_val_label = ttk.Label(self.stats_frame, text="...", style="TLabel")
        self.time_val_label.grid(row=3, column=1, sticky='w', pady=2)

        self.avg_speed_label = ttk.Label(self.stats_frame, text="Avg Speed:", style="TLabel")
        self.avg_speed_label.grid(row=4, column=0, sticky='w', padx=(0, 8), pady=2)
        self.avg_speed_val_label = ttk.Label(self.stats_frame, text="...", style="TLabel")
        self.avg_speed_val_label.grid(row=4, column=1, sticky='w', pady=2)

        # --- Progress Bar ---
        self.progress_bar = ttk.Progressbar(self.stats_frame, orient='horizontal', mode='determinate',
                                            style="Blue.TProgressbar", length=400)
        self.progressbar_border = tk.Frame(self.stats_frame, bg="#fff", bd=0, highlightthickness=0)
        self.progressbar_border.grid(row=5, column=0, columnspan=2, sticky='ew', pady=(12, 0))        
        self.progress_bar = ttk.Progressbar(self.progressbar_border, orient='horizontal', mode='determinate',
                                            style="Blue.TProgressbar", length=400)
        self.progress_bar.pack(fill='x', padx=2, pady=2)
        # self.progress_bar.grid(row=3, column=0, columnspan=2, sticky='ew', pady=(12, 0))
        self.stats_frame.columnconfigure(0, weight=1)
        self.stats_frame.columnconfigure(1, weight=1)

        # --- Status Label ---
        self.status_label = ttk.Label(self.main_frame, text="Status: Ready", anchor='w', font=("Segoe UI", 11, "italic"), style="TLabel")
        self.status_label.pack(pady=(12, 0), fill='x')

        # --- Download State Variables ---
        self.total_downloaded = 0
        self.file_size = 0
        self.last_update_time = 0
        self.last_downloaded_size = 0


    def update_progress(self, chunk_size):
        self.total_downloaded += chunk_size
        progress_percent = (self.total_downloaded / self.file_size) * 100
        self.progress_bar['value'] = progress_percent
        self.downloaded_val_label.config(text=format_bytes(self.total_downloaded))
        current_time = time.time()
        time_delta = current_time - self.last_update_time
        if time_delta >= 0.5:
            downloaded_delta = self.total_downloaded - self.last_downloaded_size
            speed = downloaded_delta / time_delta
            self.speed_val_label.config(text=f"{format_bytes(speed)}/s")
            self.last_update_time = current_time
            self.last_downloaded_size = self.total_downloaded

        # Live update total time and avg speed
        elapsed = current_time - getattr(self, 'download_start_time', current_time)
        self.time_val_label.config(text=f"{elapsed:.2f} s")
        avg_speed = self.total_downloaded / elapsed if elapsed > 0 else 0
        self.avg_speed_val_label.config(text=f"{format_bytes(avg_speed)}/s")

        self.root.update_idletasks()

    def start_download_thread(self):
        url = self.url_entry.get()
        if not url:
            messagebox.showerror("Error", "Please enter a URL.")
            return
        suggested_filename = url.split('/')[-1] or "downloaded_file"
        save_path = filedialog.asksaveasfilename(initialfile=suggested_filename)
        if not save_path:
            return
        self.reset_ui_for_download()        
        self.cancel_event.clear()  # Reset cancel event
        self.pause_event.clear()

        download_thread = threading.Thread(
            target=self.main_downloader,
            args=(url, save_path),
            daemon=True
        )
        download_thread.start()

    def cancel_download(self):
        self.cancel_event.set()
        self.status_label.config(text="Status: Cancelling...")

    def toggle_pause(self):
        if not self.pause_event.is_set():
            self.pause_event.set()
            self.pause_button.config(text="▶ Resume")
            self.status_label.config(text="Status: Paused.")
        else:
            self.pause_event.clear()
            self.pause_button.config(text="⏸ Pause")
            self.status_label.config(text="Status: Downloading...")


    def main_downloader(self, url, save_path, num_threads=10):
        self.download_start_time = time.time()
        start_time = time.time()  # Track start time

        try:
            head_response = requests.head(url, allow_redirects=True, timeout=10)
            head_response.raise_for_status()
            self.file_size = int(head_response.headers.get('content-length', 0))
        except requests.RequestException as e:
            messagebox.showerror("Error", f"Could not get file info: {e}")
            self.reset_ui_after_download()
            return

        if self.file_size == 0:
            messagebox.showerror("Error", "Could not determine file size or file is empty.")
            self.reset_ui_after_download()
            return

        self.size_val_label.config(text=format_bytes(self.file_size))
        self.status_label.config(text="Status: Downloading...")
        end_time = time.time()
        total_time = end_time - start_time
        self.time_val_label.config(text=f"{total_time:.2f} s")
        avg_speed = self.file_size / total_time if total_time > 0 else 0
        self.avg_speed_val_label.config(text=f"{format_bytes(avg_speed)}/s")
        chunk_size = self.file_size // num_threads
        threads = []
        part_files = [None] * num_threads  # Use fixed-size list

        def download_chunk_cancelable(url, start_byte, end_byte, part_num, file_path, progress_callback, cancel_event, pause_event):
            try:
                headers = {'Range': f'bytes={start_byte}-{end_byte}'}
                response = requests.get(url, headers=headers, stream=True, timeout=20)
                response.raise_for_status()
                part_filename = f"{file_path}.part{part_num}"
                with open(part_filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=16384):
                        while pause_event.is_set():
                            time.sleep(0.1)
                        if cancel_event.is_set():
                            return None
                        if chunk:
                            f.write(chunk)
                            progress_callback(len(chunk))
                return part_filename
            except requests.exceptions.RequestException:
                return None

        # Start threads, each writes to its own index in part_files
        for i in range(num_threads):
            start = i * chunk_size
            end = start + chunk_size - 1
            if i == num_threads - 1:
                end = self.file_size - 1
            def thread_func(idx=i, s=start, e=end):
                part_files[idx] = download_chunk_cancelable(
                    url, s, e, idx, save_path, self.update_progress, self.cancel_event, self.pause_event
                )
            thread = threading.Thread(target=thread_func)
            threads.append(thread)
            thread.start()

        # Wait for threads, but check for cancel to keep UI responsive
        while any(t.is_alive() for t in threads):
            if self.cancel_event.is_set():
                break
            self.root.update()
            time.sleep(0.05)

        for thread in threads:
            thread.join(timeout=0.1)

        if self.cancel_event.is_set():
            self.status_label.config(text="Status: Cancelled.")
            # Clean up partial files
            for i in range(num_threads):
                part_file = f"{save_path}.part{i}"
                if os.path.exists(part_file):
                    try:
                        os.remove(part_file)
                    except Exception:
                        pass
            self.reset_ui_after_download()
            return

        self.status_label.config(text="Status: Merging files...")
        self.speed_val_label.config(text="N/A")

        # Only keep successfully downloaded parts
        valid_parts = [f for f in part_files if f]
        if len(valid_parts) != num_threads:
            messagebox.showerror("Error", "Some parts failed to download. Aborting.")
        else:
            try:
                with open(save_path, 'wb') as final_file:
                    for part_file in sorted(valid_parts, key=lambda x: int(x.split('.part')[-1])):
                        with open(part_file, 'rb') as pf:
                            final_file.write(pf.read())
                        os.remove(part_file)
                messagebox.showinfo("Success", f"File downloaded successfully to:\n{save_path}")
            except IOError as e:
                messagebox.showerror("Error", f"Failed to merge files: {e}")

        self.reset_ui_after_download()

    def reset_ui_for_download(self):
        self.download_button.config(state="disabled")
        self.pause_button.config(state="normal", text="⏸ Pause")
        self.cancel_button.config(state="normal")
        self.progress_bar['value'] = 0
        self.total_downloaded = 0
        self.last_update_time = time.time()
        self.last_downloaded_size = 0
        self.size_val_label.config(text="...")
        self.downloaded_val_label.config(text="0 B")
        self.speed_val_label.config(text="Calculating...")


    def reset_ui_after_download(self):
        self.download_button.config(state="normal")
        self.pause_button.config(state="disabled", text="⏸ Pause")
        self.cancel_button.config(state="disabled")
        self.status_label.config(text="Status: Ready")
        self.progress_bar['value'] = 0
        self.speed_val_label.config(text="0 KB/s")
        self.time_val_label.config(text="...")
        self.avg_speed_val_label.config(text="...")

if __name__ == '__main__':
    root = tk.Tk()
    app = DownloaderApp(root)
    root.mainloop()
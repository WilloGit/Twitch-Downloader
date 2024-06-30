import tkinter as tk
import requests
from tkinter import ttk
import bs4
from tkinter import filedialog
from bs4 import BeautifulSoup
import threading
import twitchtools
from PIL import Image, ImageTk
from io import BytesIO
from datetime import datetime
from tkinter import messagebox
from downloader import TwitchDownloader


class ScrollableClipFrame(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        self.selected_clips = {}  # Changed to a dictionary to store clip data
        self.style = ttk.Style()
        self.style.configure("TFrame", background="white")
        self.style.configure("Selected.TFrame", background="#4a90e2")
        self.style.configure("Clip.TLabel", background="white")
        self.style.configure("Selected.Clip.TLabel", background="#4a90e2")

        # Create canvas
        self.canvas = tk.Canvas(self)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Bind mousewheel to scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.clip_frames = []
        self.current_row = 0
        self.current_column = 0
        self.max_columns = 3  # Adjust this value to change the number of columns

        # Bind the configure event to center the content
        self.canvas.bind("<Configure>", self.center_content)

    def center_content(self, event):
        canvas_width = event.width
        frame_width = self.scrollable_frame.winfo_reqwidth()
        if frame_width < canvas_width:
            new_x = (canvas_width - frame_width) // 2
            self.canvas.coords("all", new_x, 0)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def add_clip(self, clip):
        frame = ttk.Frame(self.scrollable_frame, width=260, height=280, style="TFrame")
        frame.grid(row=self.current_row, column=self.current_column, padx=10, pady=10, sticky="nsew")
        frame.grid_propagate(False)

        # Load and display thumbnail
        response = requests.get(clip['thumbnailURL'])
        img = Image.open(BytesIO(response.content))
        img = img.resize((240, 135), Image.LANCZOS)  # Slightly larger thumbnail
        photo = ImageTk.PhotoImage(img)
        thumbnail_label = ttk.Label(frame, image=photo, style="Clip.TLabel")
        thumbnail_label.image = photo  # Keep a reference
        thumbnail_label.pack(pady=(10, 5))

        # Display title
        title_label = ttk.Label(frame, text=clip['title'], wraplength=240, justify="center", style="Clip.TLabel")
        title_label.pack(fill="x", expand=True)

        # Display date
        created_at = datetime.fromisoformat(clip['createdAt'].rstrip('Z'))
        date_str = created_at.strftime("%Y-%m-%d %H:%M")
        date_label = ttk.Label(frame, text=f"Created: {date_str}", wraplength=240, justify="center", style="Clip.TLabel")
        date_label.pack(fill="x")

        # Display views
        views_label = ttk.Label(frame, text=f"Views: {clip['viewCount']:,}", wraplength=240, justify="center", style="Clip.TLabel")
        views_label.pack(fill="x")

        # Set initial style based on whether the clip is in selected_clips
        initial_style = "Selected.TFrame" if clip['id'] in self.selected_clips else "TFrame"
        frame.configure(style=initial_style)

        # Bind click event to the frame
        frame.bind("<Button-1>", lambda event, c=clip, f=frame: self.toggle_clip_selection(c, f))
        
        # Make sure all child widgets also trigger the selection
        for child in frame.winfo_children():
            child.bind("<Button-1>", lambda event, c=clip, f=frame: self.toggle_clip_selection(c, f))

        self.clip_frames.append((frame, clip['id']))

        # Update grid position
        self.current_column += 1
        if self.current_column >= self.max_columns:
            self.current_column = 0
            self.current_row += 1

    def toggle_clip_selection(self, clip, frame):
        if clip['id'] in self.selected_clips:
            del self.selected_clips[clip['id']]
            frame.configure(style="TFrame")
            for child in frame.winfo_children():
                if isinstance(child, ttk.Label):
                    child.configure(style="Clip.TLabel")
        else:
            self.selected_clips[clip['id']] = clip
            frame.configure(style="Selected.TFrame")
            for child in frame.winfo_children():
                if isinstance(child, ttk.Label):
                    child.configure(style="Selected.Clip.TLabel")

    def get_selected_clips(self):
        print("Inside get_selected_clips")
        print("self.selected_clips:", self.selected_clips)
        return list(self.selected_clips.values())
    
    def clear_clips(self):
        for frame, _ in self.clip_frames:
            frame.destroy()
        self.clip_frames = []
        self.current_row = 0
        self.current_column = 0
        # Note: We're not clearing selected_clips here anymore
        
    def update_selection_display(self):
        for frame, clip_id in self.clip_frames:
            if clip_id in self.selected_clips:
                frame.configure(style="Selected.TFrame")
                for child in frame.winfo_children():
                    if isinstance(child, ttk.Label):
                        child.configure(style="Selected.Clip.TLabel")
            else:
                frame.configure(style="TFrame")
                for child in frame.winfo_children():
                    if isinstance(child, ttk.Label):
                        child.configure(style="Clip.TLabel")

        
clip_fetcher = None

def create_gui(root, video_player, twitch_downloader):
    create_vod_frame(root, twitch_downloader)
    create_clip_frame(root, twitch_downloader)
    create_progress_bar(root)
    create_output_text(root)
    create_video_player_frame(root, video_player)
    create_controls_frame(root, video_player)
    create_timestamps_frame(root, video_player)

def create_vod_frame(root, twitch_downloader):
    vod_frame = tk.Frame(root)
    vod_frame.pack(pady=10)

    # Adds a label and entry for the VOD ID
    tk.Label(vod_frame, text="VOD ID:").grid(row=0, column=0, padx=10, pady=5, sticky=tk.W)
    twitch_downloader.vod_id_entry = tk.Entry(vod_frame, width=30)
    twitch_downloader.vod_id_entry.grid(row=0, column=1, padx=10, pady=5)

    # Adds a label and entry for the start time
    tk.Label(vod_frame, text="Start Time (HHMMSS):").grid(row=1, column=0, padx=10, pady=5, sticky=tk.W)
    twitch_downloader.start_time_entry = tk.Entry(vod_frame, width=30)
    twitch_downloader.start_time_entry.grid(row=1, column=1, padx=10, pady=5)

    # Adds a label and entry for the end time
    tk.Label(vod_frame, text="End Time (HHMMSS):").grid(row=2, column=0, padx=10, pady=5, sticky=tk.W)
    twitch_downloader.end_time_entry = tk.Entry(vod_frame, width=30)
    twitch_downloader.end_time_entry.grid(row=2, column=1, padx=10, pady=5)

    # Adds a button to download the VOD and chat
    download_vod_button = tk.Button(vod_frame, text="Download VOD and Chat", command=twitch_downloader.download_vod)
    download_vod_button.grid(row=3, column=0, padx=10, pady=5, columnspan=2)

def create_clip_frame(root, twitch_downloader):
    # Creates a frame for the clip ID and download/render buttons
    clip_frame = tk.Frame(root)
    clip_frame.pack(pady=10)

    # Adds a label and entry for the clip ID
    tk.Label(clip_frame, text="Clip ID:").grid(row=0, column=0, padx=10, pady=5, sticky=tk.W)
    twitch_downloader.clip_id_entry = tk.Entry(clip_frame, width=30)
    twitch_downloader.clip_id_entry.grid(row=0, column=1, padx=10, pady=5)
    
    # Adds a button to render the clip with chat
    twitch_downloader.render_chat_button = tk.Button(clip_frame, text="Render with Chat", command=twitch_downloader.render_with_chat, state="disabled")
    twitch_downloader.render_chat_button.grid(row=1, column=0, padx=10, pady=5, sticky='ew')

    # Adds a button to download the clip
    download_clip_button = tk.Button(clip_frame, text="Download Clip", command=twitch_downloader.download_clip)
    download_clip_button.grid(row=1, column=1, padx=10, pady=5, sticky='ew')
    # Adds button for bulk downloading clips
    twitch_downloader.bulk_download_clips_button = tk.Button(clip_frame, text="Bulk Download & Render", command=lambda: open_bulk_download_window(root, twitch_downloader))
    twitch_downloader.bulk_download_clips_button.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky='ew')
    
    settings_button = ttk.Button(root, text="Settings", command=lambda: open_settings_window(twitch_downloader))
    settings_button.pack(pady=10)

def open_settings_window(twitch_downloader):
    settings_window = tk.Toplevel()
    settings_window.title("Chat Overlay Settings")
    settings_window.geometry("800x600")

    # Basic Label
    label = tk.Label(settings_window, text="Chat Overlay Settings")
    label.pack(pady=20)

    # Video frame (16:9 aspect ratio)
    video_frame = tk.Frame(settings_window, width=720, height=405, bg="#2C2C2C")  # Dark gray
    video_frame.pack(pady=10)
    video_frame.pack_propagate(False)
    
    video_label = tk.Label(video_frame, text="Video Area", fg="white", bg="#2C2C2C")
    video_label.place(relx=0.5, rely=0.5, anchor="center")
    # Chat overlay (represented by a canvas)
    chat_canvas = tk.Canvas(video_frame, width=200, height=300, bg="lightgray", highlightthickness=2, highlightbackground="black")
    chat_canvas.place(x=500, y=20)
    chat_canvas.create_rectangle(0, 0, 200, 300, fill="lightgray", outline="black")
    chat_canvas.create_text(100, 150, text="Chat Overlay", fill="black")

    # Resize handles
    handle_size = 10
    handles = []
    for x, y in [(0, 0), (200, 0), (200, 300), (0, 300)]:
        handle = tk.Canvas(chat_canvas, width=handle_size, height=handle_size, bg="blue", highlightthickness=0)
        handle.place(x=x-handle_size//2, y=y-handle_size//2)
        handles.append(handle)

    # Add drag functionality to the chat overlay
    def start_drag(event):
        chat_canvas.startX = event.x
        chat_canvas.startY = event.y

    def drag(event):
        x = chat_canvas.winfo_x() - chat_canvas.startX + event.x
        y = chat_canvas.winfo_y() - chat_canvas.startY + event.y
        x = max(0, min(x, video_frame.winfo_width() - chat_canvas.winfo_width()))
        y = max(0, min(y, video_frame.winfo_height() - chat_canvas.winfo_height()))
        chat_canvas.place(x=x, y=y)

    chat_canvas.bind("<Button-1>", start_drag)
    chat_canvas.bind("<B1-Motion>", drag)

    # Add resize functionality
    def start_resize(event):
        handle = event.widget
        handle.startX = event.x
        handle.startY = event.y

    def resize(event):
        handle = event.widget
        dx = event.x - handle.startX
        dy = event.y - handle.startY
        
        x = chat_canvas.winfo_x()
        y = chat_canvas.winfo_y()
        width = chat_canvas.winfo_width()
        height = chat_canvas.winfo_height()
        
        if handle == handles[0]:  # Top-left
            new_x = max(0, min(x + dx, x + width - 50))
            new_y = max(0, min(y + dy, y + height - 50))
            new_width = max(50, min(width - dx, video_frame.winfo_width() - new_x))
            new_height = max(50, min(height - dy, video_frame.winfo_height() - new_y))
        elif handle == handles[1]:  # Top-right
            new_x = x
            new_y = max(0, min(y + dy, y + height - 50))
            new_width = max(50, min(width + dx, video_frame.winfo_width() - x))
            new_height = max(50, min(height - dy, video_frame.winfo_height() - new_y))
        elif handle == handles[2]:  # Bottom-right
            new_x = x
            new_y = y
            new_width = max(50, min(width + dx, video_frame.winfo_width() - x))
            new_height = max(50, min(height + dy, video_frame.winfo_height() - y))
        else:  # Bottom-left
            new_x = max(0, min(x + dx, x + width - 50))
            new_y = y
            new_width = max(50, min(width - dx, video_frame.winfo_width() - new_x))
            new_height = max(50, min(height + dy, video_frame.winfo_height() - y))
        
        chat_canvas.place(x=new_x, y=new_y)
        chat_canvas.config(width=new_width, height=new_height)
        
        # Update handle positions
        handles[0].place(x=-handle_size//2, y=-handle_size//2)
        handles[1].place(x=new_width-handle_size//2, y=-handle_size//2)
        handles[2].place(x=new_width-handle_size//2, y=new_height-handle_size//2)
        handles[3].place(x=-handle_size//2, y=new_height-handle_size//2)
        
        # Redraw chat overlay
        chat_canvas.delete("all")
        chat_canvas.create_rectangle(0, 0, new_width, new_height, fill="lightgray", outline="black")
        chat_canvas.create_text(new_width//2, new_height//2, text="Chat Overlay", fill="black")

    for handle in handles:
        handle.bind("<Button-1>", start_resize)
        handle.bind("<B1-Motion>", resize)

    # Save button
    save_button = tk.Button(settings_window, text="Save Settings", command=lambda: save_settings(chat_canvas, video_frame, twitch_downloader, settings_window))
    save_button.pack(pady=20)

    def configure_widgets():
        video_frame.config(width=720, height=405, bg="#2C2C2C")
        video_label.config(fg="white", bg="#2C2C2C")
        chat_canvas.config(bg="lightgray")
        
        # Print debug information
        print(f"Video frame width: {video_frame.winfo_width()}")
        print(f"Video frame height: {video_frame.winfo_height()}")
        print(f"Video frame bg color: {video_frame.cget('bg')}")
        print(f"Chat canvas width: {chat_canvas.winfo_width()}")
        print(f"Chat canvas height: {chat_canvas.winfo_height()}")
        print(f"Chat canvas bg color: {chat_canvas.cget('bg')}")

    # Schedule the configuration to occur after the window is fully created
    settings_window.after(100, configure_widgets)

def save_settings(chat_canvas, video_frame, twitch_downloader, settings_window):
    # Calculate relative positions
    x = chat_canvas.winfo_x() / video_frame.winfo_width()
    y = chat_canvas.winfo_y() / video_frame.winfo_height()
    width = chat_canvas.winfo_width() / video_frame.winfo_width()
    height = chat_canvas.winfo_height() / video_frame.winfo_height()
    
    # Save settings
    settings = {
        "chat_x": x,
        "chat_y": y,
        "chat_width": width,
        "chat_height": height
    }
    twitch_downloader.set_chat_settings(settings)
    settings_window.destroy()

def create_progress_bar(root):
    progress_bar = ttk.Progressbar(root, mode='indeterminate')
    progress_bar.pack(pady=10, fill="x", padx=20)
    return progress_bar

def create_output_text(root):
    output_text = tk.Text(root, width=80, height=10, wrap=tk.WORD)
    output_text.pack(pady=10, padx=20)
    return output_text

def create_video_player_frame(root, video_player):
    video_frame = tk.Frame(root)
    video_frame.pack(pady=10, padx=20, fill="both", expand=True)

    video_player.vid_player_canvas = tk.Canvas(video_frame, bg="black")
    video_player.vid_player_canvas.pack(fill="both", expand=True)

def create_controls_frame(root, video_player):
    controls_frame = tk.Frame(root)
    controls_frame.pack(fill="x", padx=20, expand=True)

    video_player.timestamps_canvas = tk.Canvas(controls_frame, height=20, bg="white")
    video_player.timestamps_canvas.grid(row=0, column=0, columnspan=5, sticky="ew", padx=5, pady=5)

    video_player.play_pause_text = tk.StringVar()
    video_player.play_pause_text.set("Play")

    video_player.play_pause_btn = tk.Button(controls_frame, textvariable=video_player.play_pause_text, command=video_player.play_pause, width=10, anchor='center')
    video_player.play_pause_btn.grid(row=1, column=0, padx=5, sticky='ew')

    video_player.start_time = tk.Label(controls_frame, text="00:00:00")
    video_player.start_time.grid(row=1, column=1, padx=5, sticky='ew')

    video_player.end_time = tk.Label(controls_frame, text="00:00:00")
    video_player.end_time.grid(row=1, column=2, padx=5, sticky='ew')

    video_player.mark_in_btn = tk.Button(controls_frame, text="Mark In", command=video_player.mark_in)
    video_player.mark_in_btn.grid(row=1, column=3, padx=5, sticky='ew')

    video_player.mark_out_btn = tk.Button(controls_frame, text="Mark Out", command=video_player.mark_out)
    video_player.mark_out_btn.grid(row=1, column=4, padx=5, sticky='ew')

    video_player.progress_value = tk.DoubleVar(root)
    video_player.progress_slider = tk.Scale(
        controls_frame,
        variable=video_player.progress_value,
        from_=0,
        to=100,
        orient="horizontal",
        command=video_player.seek,
        sliderlength=20
    )
    video_player.progress_slider.grid(row=2, column=0, columnspan=5, sticky="ew", padx=5)

    for i in range(5):
        controls_frame.grid_columnconfigure(i, weight=1)
    controls_frame.grid_rowconfigure(2, weight=1)

def create_timestamps_frame(root, video_player):
    timestamps_frame = tk.Frame(root)
    timestamps_frame.pack(pady=10, padx=20)

    video_player.timestamps_listbox = tk.Listbox(timestamps_frame, width=50, height=10)
    video_player.timestamps_listbox.pack(side="left", pady=5)

    delete_timestamp_btn = tk.Button(timestamps_frame, text="Delete", command=video_player.delete_timestamp)
    delete_timestamp_btn.pack(side="left", pady=5, padx=5)

    clear_timestamps_btn = tk.Button(timestamps_frame, text="Clear All", command=video_player.clear_timestamps)
    clear_timestamps_btn.pack(side="left", pady=5, padx=5)


def open_bulk_download_window(root, twitch_downloader):
    bulk_window = tk.Toplevel(root)
    bulk_window.title("Top Clips Downloader")
    bulk_window.geometry("800x600")

    ttk.Label(bulk_window, text="Streamer Username:").pack(pady=5)
    username_entry = ttk.Entry(bulk_window, width=30)
    username_entry.pack(pady=5)

    ttk.Label(bulk_window, text="Time Period:").pack(pady=5)

    time_period = tk.StringVar(bulk_window)
    time_period.set("7d")  # default value
    time_options = ["24h","24h", "7d", "30d", "all"] #extra 24h added cause it works & im lazy
    time_menu = ttk.OptionMenu(bulk_window, time_period, *time_options)
    time_menu.pack(pady=5)

    clip_frame = ScrollableClipFrame(bulk_window)
    clip_frame.pack(fill="both", expand=True, padx=10, pady=10)

    page_var = tk.IntVar(value=1)
    page_label = ttk.Label(bulk_window, text="Page: 1")
    page_label.pack()
    simultaneous_frame = ttk.Frame(bulk_window)
    simultaneous_frame.pack(pady=5)

    ttk.Label(simultaneous_frame, text="Simultaneous Downloads:").pack(side="left")
    simultaneous_var = tk.StringVar(value="3")
    simultaneous_entry = ttk.Entry(simultaneous_frame, textvariable=simultaneous_var, width=5)
    simultaneous_entry.pack(side="left", padx=5)


    def download_selected_clips():
        selected_clips = clip_frame.get_selected_clips()
        if not selected_clips:
            messagebox.showwarning("No Selection", "Please select at least one clip to download.")
            return
        
        try:
            max_workers = int(simultaneous_var.get())
            if max_workers < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number for simultaneous downloads.")
            return

        # Ask user to select a download directory
        download_dir = filedialog.askdirectory(title="Select Download Directory")
        if not download_dir:
            return  # User cancelled the folder selection

        twitch_downloader.set_max_workers(max_workers)

        progress_window = tk.Toplevel(bulk_window)
        progress_window.title("Download Progress")
        progress_window.geometry("600x400")

        progress_text = tk.Text(progress_window, wrap=tk.WORD)
        progress_text.pack(expand=True, fill="both")

        progress_bar = ttk.Progressbar(progress_window, mode='indeterminate')
        progress_bar.pack(fill="x", padx=20, pady=10)

        close_button = ttk.Button(progress_window, text="Close", command=progress_window.destroy)
        close_button.pack(pady=10)
        close_button.config(state="disabled")

        # Store the original output_text and progress_bar
        original_output_text = twitch_downloader.output_text
        original_progress_bar = twitch_downloader.progress_bar

        # Temporarily replace them with the new ones
        twitch_downloader.output_text = progress_text
        twitch_downloader.progress_bar = progress_bar

        def download_thread():
            username = username_entry.get()
            try:
                twitch_downloader.bulk_download_clips(selected_clips, download_dir, username)
                progress_window.after(0, lambda: progress_text.insert(tk.END, "All selected clips have been downloaded and processed.\n"))
            except Exception as e:
                error_message = f"An error occurred: {str(e)}\n"
                progress_window.after(0, lambda: progress_text.insert(tk.END, error_message))
            finally:
                # Restore the original output_text and progress_bar
                twitch_downloader.output_text = original_output_text
                twitch_downloader.progress_bar = original_progress_bar
                progress_window.after(0, lambda: close_button.config(state="normal"))

        thread = threading.Thread(target=download_thread)
        thread.start()

    download_button = ttk.Button(bulk_window, text="Download Selected Clips", command=download_selected_clips)
    download_button.pack(pady=10)

    def fetch_and_display_clips(page):
        username = username_entry.get()
        period = time_period.get()
        clip_fetcher = twitchtools.get_clip_fetcher(username, period)
        
        # Fetch clips for the desired page
        clips = twitchtools.fetch_clips(clip_fetcher, limit=30, page=page)
        
        clip_frame.clear_clips()
        for clip in clips:
            clip_frame.add_clip(clip)
        
        clip_frame.update_selection_display()  # Update the display to show correct selections
        
        page_label.config(text=f"Page: {page}")
        page_var.set(page)
        page_dropdown.set(page)

    def next_page():
        page_var.set(page_var.get() + 1)
        fetch_and_display_clips(page_var.get())

    def prev_page():
        if page_var.get() > 1:
            page_var.set(page_var.get() - 1)
            fetch_and_display_clips(page_var.get())

    def go_to_page(*args):
        fetch_and_display_clips(int(page_dropdown.get()))

    

    fetch_button = ttk.Button(bulk_window, text="Fetch Clips", command=lambda: fetch_and_display_clips(1))
    fetch_button.pack(pady=10)

    nav_frame = ttk.Frame(bulk_window)
    nav_frame.pack(pady=10)

    prev_button = ttk.Button(nav_frame, text="Previous Page", command=prev_page)
    prev_button.pack(side="left", padx=5)

    page_dropdown = ttk.Combobox(nav_frame, textvariable=page_var, values=list(range(1, 101)), width=5)
    page_dropdown.pack(side="left", padx=5)
    page_dropdown.bind("<<ComboboxSelected>>", go_to_page)

    next_button = ttk.Button(nav_frame, text="Next Page", command=next_page)
    next_button.pack(side="left", padx=5)
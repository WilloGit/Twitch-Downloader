import tkinter as tk
from tkinter import ttk

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

    tk.Label(vod_frame, text="VOD ID:").grid(row=0, column=0, padx=10, pady=5, sticky=tk.W)
    twitch_downloader.vod_id_entry = tk.Entry(vod_frame, width=30)
    twitch_downloader.vod_id_entry.grid(row=0, column=1, padx=10, pady=5)

    tk.Label(vod_frame, text="Start Time (HHMMSS):").grid(row=1, column=0, padx=10, pady=5, sticky=tk.W)
    twitch_downloader.start_time_entry = tk.Entry(vod_frame, width=30)
    twitch_downloader.start_time_entry.grid(row=1, column=1, padx=10, pady=5)

    tk.Label(vod_frame, text="End Time (HHMMSS):").grid(row=2, column=0, padx=10, pady=5, sticky=tk.W)
    twitch_downloader.end_time_entry = tk.Entry(vod_frame, width=30)
    twitch_downloader.end_time_entry.grid(row=2, column=1, padx=10, pady=5)

    download_vod_button = tk.Button(vod_frame, text="Download VOD and Chat", command=twitch_downloader.download_vod)
    download_vod_button.grid(row=3, column=0, padx=10, pady=5, columnspan=2)

def create_clip_frame(root, twitch_downloader):
    clip_frame = tk.Frame(root)
    clip_frame.pack(pady=10)

    tk.Label(clip_frame, text="Clip ID:").grid(row=0, column=0, padx=10, pady=5, sticky=tk.W)
    twitch_downloader.clip_id_entry = tk.Entry(clip_frame, width=30)
    twitch_downloader.clip_id_entry.grid(row=0, column=1, padx=10, pady=5)

    download_clip_button = tk.Button(clip_frame, text="Download Clip", command=twitch_downloader.download_clip)
    download_clip_button.grid(row=1, column=0, padx=10, pady=5)

    twitch_downloader.render_chat_button = tk.Button(clip_frame, text="Render with Chat", command=twitch_downloader.render_with_chat, state="disabled")
    twitch_downloader.render_chat_button.grid(row=1, column=1, padx=10, pady=5)

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

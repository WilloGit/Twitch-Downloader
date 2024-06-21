import vlc
import tkinter as tk
from tkinter import ttk
import datetime

class VideoPlayer:
    def __init__(self, root):
        self.root = root
        self.media_player = None
        self.playing = False
        self.video_duration = 0
        self.timestamps = []
        self.current_in_point = None
        self.vid_player_canvas = None
        self.timestamps_canvas = None
        self.play_pause_text = None
        self.play_pause_btn = None
        self.start_time = None
        self.end_time = None
        self.mark_in_btn = None
        self.mark_out_btn = None
        self.progress_value = None
        self.progress_slider = None
        self.timestamps_listbox = None

    def load_and_play(self, video_path):
        self.media_instance = vlc.Instance()
        self.media_player = self.media_instance.media_player_new()

        media = self.media_instance.media_new(video_path)
        self.media_player.set_media(media)
        self.media_player.set_hwnd(self.vid_player_canvas.winfo_id())

        events_manager = self.media_player.event_manager()
        events_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self.on_media_end)

        media.parse()
        self.video_duration = media.get_duration() / 1000  # Convert to seconds
        self.progress_slider.config(to=self.video_duration * 1000)  # Set the slider range
        self.end_time["text"] = str(datetime.timedelta(seconds=int(self.video_duration)))
        self.playing = False

    def play_pause(self):
        if self.playing:
            self.media_player.pause()
            self.playing = False
            self.play_pause_text.set("Play")
        else:
            self.media_player.play()
            self.playing = True
            self.play_pause_text.set("Pause")
            self.update_playback_position()

    def seek(self, value):
        time_ms = int(value)
        self.media_player.set_time(time_ms)
        if not self.playing:
            self.start_time["text"] = str(datetime.timedelta(milliseconds=float(value)))

    def mark_in(self):
        current_time = self.media_player.get_time()  # Time in milliseconds
        self.current_in_point = current_time
        formatted_time = str(datetime.timedelta(milliseconds=current_time))
        print(f"In Point: {formatted_time}")

    def mark_out(self):
        if self.current_in_point is None:
            print("Please mark the in point first.")
            return
        current_time = self.media_player.get_time()  # Time in milliseconds
        self.timestamps.append((self.current_in_point, current_time))
        formatted_in_time = str(datetime.timedelta(milliseconds=self.current_in_point))
        formatted_out_time = str(datetime.timedelta(milliseconds=current_time))
        self.timestamps_listbox.insert(
            tk.END, f"In: {formatted_in_time}, Out: {formatted_out_time}")
        print(f"Out Point: {formatted_out_time}")
        
        self.draw_timestamp_segments()
        
        self.current_in_point = None

    def draw_timestamp_segments(self):
        self.timestamps_canvas.delete("all")  # Clear previous drawings

        slider_width = self.progress_slider.winfo_width()
        max_value = self.video_duration * 1000  # Convert to milliseconds

        for (start, end) in self.timestamps:
            start_x = (start / max_value) * slider_width
            end_x = (end / max_value) * slider_width
            self.timestamps_canvas.create_rectangle(start_x, 0, end_x, 20, fill="red")

    def delete_timestamp(self):
        selected = self.timestamps_listbox.curselection()
        if not selected:
            return
        index = selected[0]
        self.timestamps_listbox.delete(index)
        del self.timestamps[index]
        self.draw_timestamp_segments()

    def clear_timestamps(self):
        self.timestamps_listbox.delete(0, tk.END)
        self.timestamps.clear()
        self.draw_timestamp_segments()

    def update_playback_position(self):
        if self.playing:
            current_time = self.media_player.get_time()  # Already in milliseconds
            self.progress_value.set(current_time)
            self.start_time["text"] = str(datetime.timedelta(milliseconds=current_time))

            if current_time >= self.video_duration * 1000:
                self.on_media_end(None)
            else:
                self.root.after(100, self.update_playback_position)  # Update

    def on_media_end(self, event):
        self.playing = False
        self.play_pause_text.set("Play")
        self.media_player.stop()
        self.progress_value.set(0)
        self.start_time["text"] = str(datetime.timedelta(seconds=0))

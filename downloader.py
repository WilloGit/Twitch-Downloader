import subprocess
import threading
import os
from queue import Queue
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from utils import is_valid_time, format_time

class TwitchDownloader:
    def __init__(self, root, video_player):
        self.root = root
        self.video_player = video_player
        self.vod_id_entry = None
        self.start_time_entry = None
        self.end_time_entry = None
        self.clip_id_entry = None
        self.render_chat_button = None
        self.bulk_download_clips_button = None
        self.output_text = None
        self.progress_bar = None


    def bulk_download_clips(self, clips, download_dir,username):
        for clip in clips:
            self.download_and_process_clip(clip, download_dir,username)


    def download_and_process_clip(self, clip, download_dir, username):
        slug = clip['slug']
        clip_id = f"https://www.twitch.tv/{username}/clip/{slug}"
        clip_title = clip['title']
        
        safe_title = "".join([c for c in clip_title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        
        # Create a temporary directory for processing
        temp_dir = os.path.join(download_dir, f"temp_{safe_title}")
        os.makedirs(temp_dir, exist_ok=True)

        try:
            # Download clip
            clip_output = os.path.join(temp_dir, f"{safe_title}_clip.mp4")
            clip_command = f"TwitchDownloaderCLI.exe clipdownload --id {clip_id} -o \"{clip_output}\""
            self.run_command(clip_command, f"Downloading Clip: {clip_title}")

            # Download chat
            chat_output = os.path.join(temp_dir, f"{safe_title}_chat.json")
            chat_command = f"TwitchDownloaderCLI.exe chatdownload --id {clip_id} --embed-images -o \"{chat_output}\""
            self.run_command(chat_command, f"Downloading Chat: {clip_title}")

            # Render chat
            render_output = os.path.join(temp_dir, f"{safe_title}_chat_render.mov")
            render_command = [
                "TwitchDownloaderCLI", "chatrender",
                "-i", chat_output,
                "-o", render_output,
                "--chat-width", "350",
                "--chat-height", "200",
                "--framerate", "30",
                "--background-color", "#8B2A2A2A",
                "--output-args=-c:v prores_ks -pix_fmt argb \"{save_path}\""
            ]
            self.run_command_shelled(render_command, f"Rendering Chat: {clip_title}")

            # Combine clip and chat
            combined_output = os.path.join(download_dir, f"{safe_title}_combined.mp4")
            combine_command = (
                f"ffmpeg.exe -i \"{clip_output}\" -i \"{render_output}\" "
                f"-filter_complex \"[1:v]scale=350:200[v1];[0:v][v1]overlay=W-w:H-h[vout]\" "
                f"-map \"[vout]\" -map 0:a \"{combined_output}\""
            )
            self.run_command(combine_command, f"Combining Clip and Chat: {clip_title}")

            self.output_text.insert(tk.END, f"Completed processing: {clip_title}\n\n")
            self.output_text.see(tk.END)

        finally:
            # Clean up temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    def download_vod(self):
        vod_id = self.vod_id_entry.get()
        start_time = self.start_time_entry.get()
        end_time = self.end_time_entry.get()

        if not vod_id:
            messagebox.showerror("Input Error", "Please enter a VOD ID.")
            return

        if start_time and not is_valid_time(start_time):
            messagebox.showerror("Input Error", "Start time must be in HHMMSS format.")
            return

        if end_time and not is_valid_time(end_time):
            messagebox.showerror("Input Error", "End time must be in HHMMSS format.")
            return

        vod_output = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 files", "*.mp4")])
        if not vod_output:
            return

        vod_command = f"TwitchDownloaderCLI.exe videodownload --id {vod_id} -o \"{vod_output}\""
        if start_time:
            vod_command += f" -b {format_time(start_time)}"
        if end_time:
            vod_command += f" -e {format_time(end_time)}"

        chat_output = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not chat_output:
            return

        chat_command = f"TwitchDownloaderCLI.exe chatdownload --id {vod_id} --embed-images -o \"{chat_output}\""
        if start_time:
            chat_command += f" -b {format_time(start_time)}"
        if end_time:
            chat_command += f" -e {format_time(end_time)}"

        render_output = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 files", "*.mp4")])
        if not render_output:
            return

        render_command = f"TwitchDownloaderCLI.exe chatrender -i \"{chat_output}\" -o \"{render_output}\" --chat-width 350 --chat-height 200 --framerate 30"
        combine_output = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 files", "*.mp4")])
        if not combine_output:
            return

        combine_command = f"ffmpeg.exe -i \"{vod_output}\" -i \"{render_output}\" -filter_complex \"[1:v]scale=350:200[v1];[0:v][v1] overlay=W-w:H-h\" -codec:a copy \"{combine_output}\""

        def task():
            self.run_command(vod_command, "Downloading VOD...")
            self.run_command(chat_command, "Downloading Chat...")
            self.run_command(render_command, "Rendering Chat...")
            self.run_command(combine_command, "Combining VOD and Chat...")

        thread = threading.Thread(target=task)
        thread.start()

    def download_clip(self):
        global clip_id, clip_output
        clip_id = self.clip_id_entry.get()

        if not clip_id:
            messagebox.showerror("Input Error", "Please enter a Clip ID.")
            return

        clip_output = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 files", "*.mp4")])
        if not clip_output:
            return

        clip_command = f"TwitchDownloaderCLI.exe clipdownload --id {clip_id} -o \"{clip_output}\""

        def download_task():
            self.run_command(clip_command, "Downloading Clip...")
            self.render_chat_button.config(state="normal")

            # Schedule video loading after a short delay
            self.root.after(100, self.video_player.load_and_play, clip_output)  

        thread = threading.Thread(target=download_task)
        thread.start()

    def render_with_chat(self):

        chat_output = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not chat_output:
            return

        chat_command = f"TwitchDownloaderCLI.exe chatdownload --id {clip_id} --embed-images -o \"{chat_output}\""

        render_output = filedialog.asksaveasfilename(
            defaultextension=".mov", 
            filetypes=[("MOV files", "*.mov")]
        )
        if not render_output:
            return

        render_command = [
            "TwitchDownloaderCLI", "chatrender",
            "-i", chat_output,
            "-o", render_output,
            "--chat-width", "350",
            "--chat-height", "200",
            "--framerate", "30",
            "--background-color", "#8B2A2A2A",
            "--output-args=-c:v prores_ks -pix_fmt argb \"{save_path}\""
        ]

        combine_output = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 files", "*.mp4")])
        if not combine_output:
            return

        def generate_mute_filter(segments):
            if not segments:
                return None
            filter_parts = []
            for start_ms, end_ms in segments:
                start_sec = start_ms / 1000
                end_sec = end_ms / 1000
                filter_parts.append(f"volume=enable='between(t,{start_sec},{end_sec})':volume=0")
            return ",".join(filter_parts)
        
        mute_filter = generate_mute_filter(self.video_player.timestamps)

        filter_complex = "[1:v]scale=350:200[v1];[0:v][v1]overlay=W-w:H-h[vout]"
        if mute_filter:
            filter_complex += f";[0:a]{mute_filter}[aout]"
            audio_map = "-map \"[aout]\""
        else:
            audio_map = "-map 0:a"

        combine_command = (
            f"ffmpeg.exe -i \"{clip_output}\" -i \"{render_output}\" "
            f"-filter_complex \"{filter_complex}\" "
            f"-map \"[vout]\" {audio_map} \"{combine_output}\""
        )

        def render_task():
            self.run_command(chat_command, "Downloading Chat...")
            self.run_command_shelled(render_command, "Rendering Chat...")
            self.run_command(combine_command, "Combining Clip and Chat...")

        thread = threading.Thread(target=render_task)
        thread.start()

    def run_command(self, command, description):
        self.progress_bar.start()
        self.output_text.insert(tk.END, f"{description}\n")
        self.output_text.see(tk.END)
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                self.output_text.insert(tk.END, "Completed Successfully\n")
            else:
                self.output_text.insert(tk.END, f"Error: {result.stderr}\n")
        finally:
            self.progress_bar.stop()
            self.output_text.insert(tk.END, "\n")
            self.output_text.see(tk.END)

    def run_command_shelled(self, command, description):
        self.progress_bar.start()
        self.output_text.insert(tk.END, f"{description}\n")
        self.output_text.see(tk.END)
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            if result.returncode == 0:
                self.output_text.insert(tk.END, "Completed Successfully\n")
            else:
                self.output_text.insert(tk.END, f"Error: {result.stderr}\n")
        except Exception as e:
            self.output_text.insert(tk.END, f"Exception: {str(e)}\n")
        finally:
            self.progress_bar.stop()
            self.output_text.insert(tk.END, "\n")
            self.output_text.see(tk.END)

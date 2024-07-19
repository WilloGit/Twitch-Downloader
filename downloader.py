import subprocess
import concurrent.futures
import threading
import os
import json
import time
import queue
from queue import Queue
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from utils import is_valid_time, format_time
import assemblyai as aai
import re
import logging
import traceback
# Replace with your API key
aai.settings.api_key = os.getenv("ASSEMBLY_API_KEY")


class TwitchDownloader:
    def __init__(self, root, video_player=None):
        self.root = root
        self.vod_url_entry = None
        self.video_player = video_player
        self.timestamps_text = None
        self.vod_id_entry = None
        self.start_time_entry = None
        self.end_time_entry = None
        self.clip_id_entry = None
        self.render_chat_button = None
        self.bulk_download_clips_button = None
        self.output_text = None
        self.progress_bar = None
        self.processing_queue = Queue()
        self.render_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)  # Adjust max_workers as needed
        self.render_lock = threading.Lock()
        self.processing_thread = None
        self.settings_file = "settings.json"
        loaded_settings = self.load_settings()
        self.chat_settings = loaded_settings["chat_settings"]
        self.max_workers = loaded_settings["max_workers"]

    def load_settings(self):
        default_settings = {
            "chat_settings": {
                "chat_x": 0.7611111111111111,
                "chat_y": 0.38765432098765434,
                "chat_width": 0.2388888888888889,
                "chat_height": 0.6123456790123457,
                "font_size": 24,
                "background_color": "40808080"
            },
            "max_workers": 3
        }
        try:
            with open(self.settings_file, "r") as f:
                loaded_settings = json.load(f)
            # Ensure all expected keys are present
            for key in default_settings:
                if key not in loaded_settings:
                    loaded_settings[key] = default_settings[key]
            return loaded_settings
        except FileNotFoundError:
            return default_settings

    def save_settings(self):
        settings = {
            "chat_settings": self.chat_settings,
            "max_workers": self.max_workers
        }
        with open(self.settings_file, "w") as f:
            json.dump(settings, f, indent=4)

    def set_chat_settings(self, settings):
        self.chat_settings.update(settings)
        self.save_settings()

    def set_max_workers(self, workers):
        self.max_workers = workers
        self.save_settings()
    #MIGHT BE REDUNDANT
    def set_progress_bar(self, progress_bar):
        self.progress_bar = progress_bar

    def set_output_text(self, output_text):
        self.output_text = output_text

    def bulk_download_clips(self, clips, download_dir, username):
        self.processing_queue = queue.Queue()
        for clip in clips:
            self.processing_queue.put((clip, download_dir, username))
        
        self.processing_thread = threading.Thread(target=self.process_queue)
        self.processing_thread.start()
        
        # Wait for the processing to complete, but with a timeout
        start_time = time.time()
        while self.processing_thread.is_alive():
            if time.time() - start_time > 3600:  # 1 hour timeout
                self.safe_output_text_insert("Bulk download timed out after 1 hour\n")
                break
            time.sleep(1)
        
        self.safe_output_text_insert("Bulk download completed or timed out\n")


    def process_queue(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            while not self.processing_queue.empty():
                try:
                    clip, download_dir, username = self.processing_queue.get(block=False)
                    future = executor.submit(self.download_and_process_clip, clip, download_dir, username)
                    futures.append(future)
                except queue.Empty:
                    break
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()  # This will raise any exceptions that occurred during processing
                except Exception as e:
                    self.output_text.insert(tk.END, f"Error processing clip: {str(e)}\n")
                    self.output_text.see(tk.END)



    def transcribe_audio(self, audio_file):
        try:
            transcriber = aai.Transcriber()
            transcript = transcriber.transcribe(audio_file)
            
            if transcript.status == aai.TranscriptStatus.error:
                self.safe_output_text_insert(f"Transcription error: {transcript.error}\n")
                return None, []
            
            swear_patterns = [
                r'\bf[u\*]+ck',
                r'\bsh[i\*]+t',
                r'\bd[a\*]+mn',
                r'\bb[i\*]+tch',
                r'\ba[s\*]+',
                r'\bmotherfuck',
                r'\bretard(?:s|ed)?',
                r'\bcunts?',
                r'\bd[i\*]+ck',
                r'\bp[e\*]+nis',
            ]
            swear_regex = re.compile('|'.join(swear_patterns), re.IGNORECASE)
            swear_timestamps = []

            for word in transcript.words:
                if swear_regex.search(word.text):
                    swear_timestamps.append((word.text, word.start, word.end))
            
            return transcript, swear_timestamps
        except Exception as e:
            self.safe_output_text_insert(f"Transcription failed: {str(e)}\n")
            return None, []

    def download_vod_segments(self, vod_url, timestamps, download_dir):
        try:
            logging.debug(f"Starting download_vod_segments with {len(timestamps)} timestamps")
            self.processing_queue = queue.Queue()
            for i, timestamp in enumerate(timestamps, 1):
                self.processing_queue.put((i, timestamp, vod_url, download_dir))
            
            self.process_vod_segments_queue()
        except Exception as e:
            logging.error(f"Error in download_vod_segments: {str(e)}")
            logging.error(traceback.format_exc())
            self.safe_output_text_insert(f"Error starting VOD segment download: {str(e)}\n")
            messagebox.showerror("Error", f"An error occurred while starting the download: {str(e)}")

    def process_vod_segments_queue(self):
        try:
            logging.debug("Starting process_vod_segments_queue")
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                while not self.processing_queue.empty():
                    try:
                        segment_info = self.processing_queue.get(block=False)
                        future = executor.submit(self.process_vod_segment, *segment_info)
                        futures.append(future)
                    except queue.Empty:
                        break
                
                for future in concurrent.futures.as_completed(futures):
                    try:
                        future.result()  # This will raise any exceptions that occurred during processing
                    except Exception as e:
                        logging.error(f"Error processing segment: {str(e)}")
                        logging.error(traceback.format_exc())
                        self.safe_output_text_insert(f"Error processing segment: {str(e)}\n")

            self.safe_output_text_insert("All VOD segments have been processed.\n")
            messagebox.showinfo("Download Complete", "All VOD segments have been downloaded and processed.")
        except Exception as e:
            logging.error(f"Error in process_vod_segments_queue: {str(e)}")
            logging.error(traceback.format_exc())
            self.safe_output_text_insert(f"Error processing VOD segments: {str(e)}\n")
            messagebox.showerror("Error", f"An error occurred while processing VOD segments: {str(e)}")


    def process_vod_segment(self, i, timestamp, vod_url, download_dir):
        temp_dir = None
        try:
            logging.debug(f"Processing segment {i}: {timestamp}")
            start_time, end_time = timestamp.split('-')
            temp_dir = os.path.join(download_dir, f"temp_segment_{i}")
            os.makedirs(temp_dir, exist_ok=True)
            
            # Download video segment
            output_file = os.path.join(temp_dir, f"segment_{i}.mp4")
            self.download_vod_segment(vod_url, start_time, end_time, output_file)

            # Download chat
            chat_output = os.path.join(temp_dir, f"segment_{i}_chat.json")
            self.download_vod_chat(vod_url, start_time, end_time, chat_output)

            # Transcribe audio and detect swear words
            transcript, swear_timestamps = self.transcribe_audio(output_file)

            # Render chat
            render_future = self.render_pool.submit(self.render_chat, chat_output, temp_dir, f"segment_{i}")
            
            # Combine video and chat, and mute swear words
            combined_output = os.path.join(download_dir, f"segment_{i}_combined.mp4")
            self.wait_and_combine_vod(render_future, output_file, combined_output, swear_timestamps)

            self.safe_output_text_insert(f"Completed processing segment {i}\n")
        except Exception as e:
            logging.error(f"Error processing segment {i}: {str(e)}")
            logging.error(traceback.format_exc())
            self.safe_output_text_insert(f"Error processing segment {i}: {str(e)}\n")
        finally:
            # Clean up temporary directory
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)


    def download_vod_segment(self, vod_url, start_time, end_time, output_file):
        command = [
            "TwitchDownloaderCLI.exe",
            "videodownload",
            "-u", vod_url,
            "-o", output_file,
            "-b", start_time,
            "-e", end_time
            ]
        self.run_command(command, f"Downloading VOD segment ({start_time} to {end_time})")
    def download_vod_chat(self, vod_url, start_time, end_time, chat_output):
        command = [
            "TwitchDownloaderCLI.exe",
            "chatdownload",
            "-u", vod_url,
            "-o", chat_output,
            "-b", start_time,
            "-e", end_time
        ]
        self.run_command(command, f"Downloading chat ({start_time} to {end_time})")

    def wait_and_combine_vod(self, render_future, video_file, combined_output, swear_timestamps):
        render_output = render_future.result()
        x = int(self.chat_settings["chat_x"] * 1920)
        y = int(self.chat_settings["chat_y"] * 1080)
        
        # Generate mute filter for swear words
        mute_filter = self.generate_mute_filter(swear_timestamps)
        
        combine_command = [
            "ffmpeg",
            "-i", video_file,
            "-i", render_output,
            "-filter_complex",
            f"[1:v]scale={int(self.chat_settings['chat_width'] * 1920)}:{int(self.chat_settings['chat_height'] * 1080)}[chat];"
            f"[0:v][chat]overlay={x}:{y}[v];"
            f"{mute_filter}",
            "-map", "[v]",
            "-map", "[aout]",
            combined_output
        ]
        self.run_command(combine_command, f"Combining video and chat")


    def safe_progress_bar_start(self):
        if self.progress_bar:
            self.progress_bar.start()
        else:
            print("Warning: Progress bar not initialized")  # Or use logging.warning()

    def download_and_process_clip(self, clip, download_dir, username):
        if 'slug' in clip:
            slug = clip['slug']
            clip_id = f"https://clips.twitch.tv/{slug}"
            clip_title = clip['title']
        else:
            clip_id = clip['id']
            clip_title = clip['title']
        
        safe_title = "".join([c for c in clip_title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        
        temp_dir = os.path.join(download_dir, f"temp_{safe_title}")
        os.makedirs(temp_dir, exist_ok=True)

        try:
            # Download clip and chat
            clip_output = self.download_clip(clip_id, temp_dir, safe_title)
            chat_output = self.download_chat(clip_id, temp_dir, safe_title)

            # Transcribe audio and detect swear words
            transcript, swear_timestamps = self.transcribe_audio(clip_output)

            # Submit render and combine tasks to the thread pool
            render_future = self.render_pool.submit(self.render_chat, chat_output, temp_dir, safe_title)
            combine_future = self.render_pool.submit(self.wait_and_combine, render_future, clip_output, download_dir, safe_title, clip_title, swear_timestamps)

            # Wait for the combine task to complete with a timeout
            combine_future.result(timeout=600)  # 10 minutes timeout

            with self.render_lock:
                self.safe_output_text_insert(f"Completed processing: {clip_title}\n\n")
        except concurrent.futures.TimeoutError:
            with self.render_lock:
                self.safe_output_text_insert(f"Timeout while processing {clip_title}\n\n")
        except Exception as e:
            with self.render_lock:
                self.safe_output_text_insert(f"Error processing {clip_title}: {str(e)}\n\n")
        finally:
            # Clean up temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    
    # def download_vod(self):
    #     vod_id = self.vod_id_entry.get()
    #     start_time = self.start_time_entry.get()
    #     end_time = self.end_time_entry.get()

    #     if not vod_id:
    #         messagebox.showerror("Input Error", "Please enter a VOD ID.")
    #         return

    #     if start_time and not is_valid_time(start_time):
    #         messagebox.showerror("Input Error", "Start time must be in HHMMSS format.")
    #         return

    #     if end_time and not is_valid_time(end_time):
    #         messagebox.showerror("Input Error", "End time must be in HHMMSS format.")
    #         return

    #     vod_output = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 files", "*.mp4")])
    #     if not vod_output:
    #         return

    #     vod_command = f"TwitchDownloaderCLI.exe videodownload --id {vod_id} -o \"{vod_output}\""
    #     if start_time:
    #         vod_command += f" -b {format_time(start_time)}"
    #     if end_time:
    #         vod_command += f" -e {format_time(end_time)}"

    #     chat_output = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
    #     if not chat_output:
    #         return

    #     chat_command = f"TwitchDownloaderCLI.exe chatdownload --id {vod_id} --embed-images -o \"{chat_output}\""
    #     if start_time:
    #         chat_command += f" -b {format_time(start_time)}"
    #     if end_time:
    #         chat_command += f" -e {format_time(end_time)}"

    #     render_output = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 files", "*.mp4")])
    #     if not render_output:
    #         return

    #     render_command = f"TwitchDownloaderCLI.exe chatrender -i \"{chat_output}\" -o \"{render_output}\" --chat-width 350 --chat-height 200 --framerate 30"
    #     combine_output = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 files", "*.mp4")])
    #     if not combine_output:
    #         return

    #     combine_command = f"ffmpeg.exe -i \"{vod_output}\" -i \"{render_output}\" -filter_complex \"[1:v]scale=350:200[v1];[0:v][v1] overlay=W-w:H-h\" -codec:a copy \"{combine_output}\""

    #     def task():
    #         self.run_command(vod_command, "Downloading VOD...")
    #         self.run_command(chat_command, "Downloading Chat...")
    #         self.run_command(render_command, "Rendering Chat...")
    #         self.run_command(combine_command, "Combining VOD and Chat...")

    #     thread = threading.Thread(target=task)
    #     thread.start()

    def download_clip(self, clip_id, temp_dir, safe_title):
        clip_output = os.path.join(temp_dir, f"{safe_title}_clip.mp4")
        clip_command = f"TwitchDownloaderCLI.exe clipdownload --id {clip_id} -o \"{clip_output}\""
        self.run_command(clip_command, f"Downloading Clip: {safe_title}")
        return clip_output
    

    def download_chat(self, clip_id, temp_dir, safe_title):
        chat_output = os.path.join(temp_dir, f"{safe_title}_chat.json")
        chat_command = f"TwitchDownloaderCLI.exe chatdownload --id {clip_id} --embed-images -o \"{chat_output}\""
        self.run_command(chat_command, f"Downloading Chat: {safe_title}")
        return chat_output

    def render_chat(self, chat_output, temp_dir, safe_title):
        render_output = os.path.join(temp_dir, f"{safe_title}_chat_render.mov")
        render_command = [
            "TwitchDownloaderCLI", "chatrender",
            "-i", chat_output,
            "-o", render_output,
            "--font-size", str(int(self.chat_settings["font_size"])),
            "--chat-width", str(int(self.chat_settings["chat_width"] * 1920)),
            "--chat-height", str(int(self.chat_settings["chat_height"] * 1080)),
            "--framerate", "12",
            "--background-color", "#"+str(self.chat_settings["background_color"]),
            "--output-args=-c:v prores_ks -pix_fmt argb \"{save_path}\""
        ]
        self.run_command_shelled(render_command, f"Rendering Chat: {safe_title}")
        return render_output

    def wait_and_combine(self, render_future, clip_output, download_dir, safe_title, clip_title, swear_timestamps):
        try:
            render_output = render_future.result(timeout=300)  # 5 minutes timeout
            combined_output = os.path.join(download_dir, f"{safe_title}_combined.mp4")
            self.combine_clip_and_chat(clip_output, render_output, combined_output, clip_title, swear_timestamps)
        except concurrent.futures.TimeoutError:
            self.safe_output_text_insert(f"Timeout while waiting for chat render: {clip_title}\n")
        except Exception as e:
            self.safe_output_text_insert(f"Error in wait_and_combine for {clip_title}: {str(e)}\n")

    def combine_clip_and_chat(self, clip_output, render_output, combined_output, clip_title, swear_timestamps):
        x = int(self.chat_settings["chat_x"] * 1920)
        y = int(self.chat_settings["chat_y"] * 1080)
        
        mute_filter = self.generate_mute_filter(swear_timestamps)
        
        combine_command = (
            f"ffmpeg.exe -i \"{clip_output}\" -i \"{render_output}\" "
            f"-filter_complex \"[1:v]scale={int(self.chat_settings['chat_width'] * 1920)}:{int(self.chat_settings['chat_height'] * 1080)}[v1];"
            f"[0:v][v1]overlay={x}:{y}[vout];"
            f"{mute_filter}\" "
            f"-map \"[vout]\" -map \"[aout]\" \"{combined_output}\""
        )
        with self.render_lock:
            self.safe_output_text_insert(f"Starting to combine Clip and Chat: {clip_title}\n")
            process = subprocess.Popen(combine_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            while True:
                output = process.stderr.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    self.safe_output_text_insert(f"FFmpeg: {output.strip()}\n")
            
            rc = process.poll()
            if rc == 0:
                self.safe_output_text_insert(f"Successfully combined Clip and Chat: {clip_title}\n")
            else:
                self.safe_output_text_insert(f"Error combining Clip and Chat: {clip_title}. Return code: {rc}\n")

    def generate_mute_filter(self, timestamps):
        if not timestamps:
            return "[0:a]acopy[aout]"
        
        filter_parts = []
        for _, start, end in timestamps:
            start_sec = start / 1000
            end_sec = end / 1000
            filter_parts.append(f"volume=enable='between(t,{start_sec},{end_sec})':volume=0")
        
        return f"[0:a]{','.join(filter_parts)}[aout]"

    def shutdown(self):
        self.render_pool.shutdown(wait=True)


    # def render_with_chat(self):
    #     chat_output = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
    #     if not chat_output:
    #         return

    #     chat_command = f"TwitchDownloaderCLI.exe chatdownload --id {clip_id} --embed-images -o \"{chat_output}\""

    #     render_output = filedialog.asksaveasfilename(
    #         defaultextension=".mov", 
    #         filetypes=[("MOV files", "*.mov")]
    #     )
    #     if not render_output:
    #         return

    #     render_command = [
    #         "TwitchDownloaderCLI", "chatrender",
    #         "-i", chat_output,
    #         "-o", render_output,
    #         "--chat-width", "350",
    #         "--chat-height", "200",
    #         "--framerate", "30",
    #         "--background-color", "#8B2A2A2A",
    #         "--output-args=-c:v prores_ks -pix_fmt argb \"{save_path}\""
    #     ]

    #     combine_output = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 files", "*.mp4")])
    #     if not combine_output:
    #         return

    #     def generate_mute_filter(segments):
    #         if not segments:
    #             return None
    #         filter_parts = []
    #         for start_ms, end_ms in segments:
    #             start_sec = start_ms / 1000
    #             end_sec = end_ms / 1000
    #             filter_parts.append(f"volume=enable='between(t,{start_sec},{end_sec})':volume=0")
    #         return ",".join(filter_parts)
        
    #     mute_filter = generate_mute_filter(self.video_player.timestamps)

    #     filter_complex = "[1:v]scale=350:200[v1];[0:v][v1]overlay=W-w:H-h[vout]"
    #     if mute_filter:
    #         filter_complex += f";[0:a]{mute_filter}[aout]"
    #         audio_map = "-map \"[aout]\""
    #     else:
    #         audio_map = "-map 0:a"

    #     combine_command = (
    #         f"ffmpeg.exe -i \"{clip_output}\" -i \"{render_output}\" "
    #         f"-filter_complex \"{filter_complex}\" "
    #         f"-map \"[vout]\" {audio_map} \"{combine_output}\""
    #     )

    #     def render_task():
    #         self.run_command(chat_command, "Downloading Chat...")
    #         self.run_command_shelled(render_command, "Rendering Chat...")
    #         self.run_command(combine_command, "Combining Clip and Chat...")

    #     thread = threading.Thread(target=render_task)
    #     thread.start()


    def safe_progress_bar_start(self):
        if self.progress_bar:
            self.progress_bar.start()
        else:
            print("Warning: Progress bar not initialized")

    def safe_progress_bar_stop(self):
        if self.progress_bar:
            self.progress_bar.stop()
        else:
            print("Warning: Progress bar not initialized")

    def safe_output_text_insert(self, message):
        if self.output_text:
            self.output_text.insert(tk.END, message)
            self.output_text.see(tk.END)
        else:
            print(f"Output: {message}")



    def run_command(self, command, description):
        self.safe_progress_bar_start()
        self.safe_output_text_insert(f"{description}\n")
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            self.safe_output_text_insert("Command completed successfully\n")
        except subprocess.CalledProcessError as e:
            self.safe_output_text_insert(f"Error: {e.stderr}\n")
        finally:
            self.safe_progress_bar_stop()
            self.safe_output_text_insert("\n")


    def run_command_shelled(self, command, description):
        if self.progress_bar:
            self.progress_bar.start()
        if self.output_text:
            self.output_text.insert(tk.END, f"{description}\n")
            self.output_text.see(tk.END)
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            if result.returncode == 0:
                if self.output_text:
                    self.output_text.insert(tk.END, "Completed Successfully\n")
            else:
                if self.output_text:
                    self.output_text.insert(tk.END, f"Error: {result.stderr}\n")
        except Exception as e:
            if self.output_text:
                self.output_text.insert(tk.END, f"Exception: {str(e)}\n")
        finally:
            if self.progress_bar:
                self.progress_bar.stop()
            if self.output_text:
                self.output_text.insert(tk.END, "\n")
                self.output_text.see(tk.END)

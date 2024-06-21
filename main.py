import tkinter as tk
from ttkbootstrap import Style
from gui import create_gui
from player import VideoPlayer
from downloader import TwitchDownloader

def main():
    style = Style('lumen')
    root = style.master
    root.title("Twitch Downloader GUI")

    video_player = VideoPlayer(root)
    twitch_downloader = TwitchDownloader(root, video_player)
    
    create_gui(root, video_player, twitch_downloader)

    root.mainloop()

if __name__ == "__main__":
    main()

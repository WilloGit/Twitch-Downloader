import tkinter as tk
from tkinter import ttk
from ttkbootstrap import Style

def open_test_window():
    test_window = tk.Toplevel()
    test_window.title("Test Window")
    test_window.geometry("600x600")  # Increased initial size

    # Test 1: Basic Label
    label = ttk.Label(test_window, text="Test Label", style="TLabel")
    label.pack(pady=10)

    # Test 2: Frame with pack (Red)
    frame_pack = ttk.Frame(test_window, width=200, height=100, style="Red.TFrame")
    frame_pack.pack(pady=10)
    frame_pack.pack_propagate(False)
    ttk.Label(frame_pack, text="Red Frame", style="Red.TLabel").place(relx=0.5, rely=0.5, anchor="center")

    # Test 3: Another Frame with pack (Blue)
    frame_pack2 = ttk.Frame(test_window, width=200, height=100, style="Blue.TFrame")
    frame_pack2.pack(pady=10)
    frame_pack2.pack_propagate(False)
    ttk.Label(frame_pack2, text="Blue Frame", style="Blue.TLabel").place(relx=0.5, rely=0.5, anchor="center")

    # Test 4: Canvas
    canvas = tk.Canvas(test_window, width=200, height=100, bg="yellow", highlightthickness=2, highlightbackground="black")
    canvas.pack(pady=10)
    canvas.create_rectangle(0, 0, 200, 100, fill="yellow", outline="black")
    canvas.create_text(100, 50, text="Yellow Canvas", fill="black")

    # Test 5: Colored Frame (Green)
    colored_frame = ttk.Frame(test_window, width=200, height=100, style="Green.TFrame")
    colored_frame.pack(pady=10)
    colored_frame.pack_propagate(False)
    ttk.Label(colored_frame, text="Green Frame", style="Green.TLabel").place(relx=0.5, rely=0.5, anchor="center")

    def print_info():
        print("Test window opened")
        print(f"Red Frame width: {frame_pack.winfo_width()}")
        print(f"Red Frame height: {frame_pack.winfo_height()}")
        print(f"Red Frame visible: {frame_pack.winfo_viewable()}")
        print(f"Blue Frame width: {frame_pack2.winfo_width()}")
        print(f"Blue Frame height: {frame_pack2.winfo_height()}")
        print(f"Blue Frame visible: {frame_pack2.winfo_viewable()}")
        print(f"Canvas width: {canvas.winfo_width()}")
        print(f"Canvas height: {canvas.winfo_height()}")
        print(f"Canvas visible: {canvas.winfo_viewable()}")
        print(f"Green Frame width: {colored_frame.winfo_width()}")
        print(f"Green Frame height: {colored_frame.winfo_height()}")
        print(f"Green Frame visible: {colored_frame.winfo_viewable()}")

    # Force update and print info after a short delay
    test_window.update_idletasks()
    test_window.after(100, print_info)

    # Attempt to force sizes
    frame_pack.config(width=200, height=100)
    frame_pack2.config(width=200, height=100)
    canvas.config(width=200, height=100)
    colored_frame.config(width=200, height=100)

    # Print info again after forcing sizes
    test_window.after(200, print_info)

    # Attempt to force sizes
    frame_pack.config(width=200, height=100)
    frame_pack2.config(width=200, height=100)
    canvas.config(width=200, height=100)
    colored_frame.config(width=200, height=100)

    # Print info again after forcing sizes
    test_window.after(200, print_info)

def main():
    style = Style(theme='lumen')
    root = style.master
    root.title("Test App")

    style.configure("TLabel", foreground="black")
    style.configure("Red.TFrame", background="red")
    style.configure("Red.TLabel", background="red", foreground="white")
    style.configure("Blue.TFrame", background="blue")
    style.configure("Blue.TLabel", background="blue", foreground="white")
    style.configure("Green.TFrame", background="lightgreen")
    style.configure("Green.TLabel", background="lightgreen", foreground="black")

    open_button = ttk.Button(root, text="Open Test Window", command=open_test_window)
    open_button.pack(pady=20)

    root.mainloop()

if __name__ == "__main__":
    main()
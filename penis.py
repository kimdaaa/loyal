
from os import system
import asyncio
from player_stats import PlayerStats
from rank import Rank
from rpc import Rpc
from content import Content
from Request1 import Requests
from States.coregame import Coregame
from States.menu import Menu
from States.pregame import Pregame
from names import Names
from utils import utilities
from presence import Presences
import urllib3
import time
from pathlib import Path
from tkinter import Tk, Canvas, Entry, Text, Button, PhotoImage
import tkinter as tk
import sys
from PIL import Image, ImageTk
system('cls') 

Requests = Requests()
presences = Presences(Requests,)
content = Content(Requests)
Pregame = Pregame(Requests)
menu = Menu(Requests, presences)
coregame = Coregame(Requests)
utilities = utilities(Requests)
OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / Path(r"C:\Users\ihatewindowsthemost\Desktop\Ur mum\frame0")
firstTime = True
firstPrint = True


def relative_to_assets(path: str) -> Path:
    """Generate path relative to the assets directory."""
    return Path(__file__).parent / 'frame0' / path

def create_rounded_rectangle(canvas, x1, y1, x2, y2, radius, **kwargs):
    """Create a rounded rectangle on the canvas."""
    points = [
        (x1 + radius, y1), (x2 - radius, y1),
        (x2, y1), (x2, y1 + radius),
        (x2, y2 - radius), (x2, y2),
        (x2 - radius, y2), (x1 + radius, y2),
        (x1, y2), (x1, y2 - radius),
        (x1, y1 + radius), (x1, y1)
    ]
    return canvas.create_polygon(
        points,
        smooth=True,
        **kwargs
    )

class TextRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, text):
        self.text_widget.insert(tk.END, text)
        self.text_widget.see(tk.END)

    def flush(self):
        pass

class GUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("770x389")
        self.configure(bg="#1A181B")
        self.title("Loyal V1")
        self.resizable(False, False)
        self.setup_icon()
        self.setup_widgets()
        self.redirect_stdout()

    def setup_icon(self):
        """Loads and sets the window icon."""
        ico_path = relative_to_assets('icon.ico')
        icon_image = ImageTk.PhotoImage(file=ico_path)
        self.iconphoto(True, icon_image)

    def setup_widgets(self):
        """Sets up the GUI widgets."""
        self.canvas = Canvas(
            self,
            bg="#1A181B",
            height=389,
            width=770,
            bd=0,
            highlightthickness=0,
            relief="ridge"
        )
        self.canvas.place(x=0, y=0)
        self.create_rounded_rectangle(10, 10, 760, 379, 20, fill="#000000")

        # Add rectangles for data
        self.setup_data_boxes()
        self.setup_lines()
        self.setup_entry()
        self.setup_buttons()
        self.setup_labels()

    def create_rounded_rectangle(self, x1, y1, x2, y2, radius, **kwargs):
        """Create a rounded rectangle on the canvas."""
        points = [
            (x1 + radius, y1), (x2 - radius, y1),
            (x2, y1), (x2, y1 + radius),
            (x2, y2 - radius), (x2, y2),
            (x2 - radius, y2), (x1 + radius, y2),
            (x1, y2), (x1, y2 - radius),
            (x1, y1 + radius), (x1, y1)
        ]
        return self.canvas.create_polygon(
            points,
            smooth=True,
            **kwargs
        )

    def setup_data_boxes(self):
        """Setup data boxes on the canvas."""
        positions = [
            (340, 60, 440, 254),
            (492, 60, 592, 254),
            (640, 60, 740, 254),
            (41, 60, 141, 254),
            (189, 60, 289, 254)
        ]
        radius = 10
        for pos in positions:
            self.create_rounded_rectangle(pos[0], pos[1], pos[2], pos[3], radius, fill="#b0afb4")

    def setup_lines(self):
        """Draw lines on the canvas."""
        line_positions = [
            (615, 50, 616, 379), (164, 50, 165, 267), (315, 50, 316, 267),
            (464, 50, 465, 267), (10, 50, 760, 50)
        ]
        for line in line_positions:
            self.canvas.create_line(*line, fill="#53d07a", width=2)

    def setup_entry(self):
        """Setup entry widget."""
        self.entry_1 = Text(
            self, bd=2, bg="#000716", fg="#3E5D65", highlightthickness=0,
        )
        self.entry_1.place(x=39, y=267, width=571, height=109)

    def setup_buttons(self):
        """Setup buttons."""
        button_positions = [(625, 304), (625, 267), (625, 341)]
        button_images = ["button_1.png", "button_2.png", "button_3.png"]
        commands = [self.dodge, self.start_queue, self.solo_exp]
        self.buttons = []
        for pos, img, cmd in zip(button_positions, button_images, commands):
            photo = PhotoImage(file=relative_to_assets(img))
            button = Button(
                self, image=photo, borderwidth=0, highlightthickness=0,
                command=lambda cmd=cmd: cmd(), relief="flat"
            )
            button.image = photo  # keep a reference
            button.place(x=pos[0], y=pos[1], width=131, height=37)
            self.buttons.append(button)

    def setup_labels(self):
        """Setup labels with rounded corners."""
        positions = [
            (30, 10, 150, 40), (180, 10, 300, 40),
            (331, 10, 451, 40), (482, 10, 602, 40),
            (630, 10, 750, 40)
        ]
        texts = ["tt"] * 5
        radius = 10  # Radius for rounded corners
        for pos, text in zip(positions, texts):
            self.create_rounded_rectangle(pos[0], pos[1], pos[2], pos[3], radius, fill="#5e859b")
            self.canvas.create_text(pos[0] + 20, pos[1] + 15, anchor="nw", text=text, fill="#FFFFFF", font=("Inter", 12))

    def dodge(self):
        """Stub function for Dodge action."""
        a = Pregame.get_pregame_match_id()
        print('[+] Game has been dodged')
        utilities.dodge(a)

    def start_queue(self):
        """Stub function for Start Queue."""
        a = menu.get_party_id(puuid=Requests.puuid)
        utilities.Queue(a)
        print('[+] Queue has started')

    def solo_exp(self):
        """Stub function for Solo Experience."""
        b = Pregame.Hover()
        print(b)
        print('[+] Character Locked')

    def redirect_stdout(self):
        """Redirect stdout to the Text widget."""
        sys.stdout = TextRedirector(self.entry_1)
        sys.stderr = TextRedirector(self.entry_1)  # Also redirect stderr if desired

if __name__ == "__main__":
    app = GUI()
    app.mainloop()

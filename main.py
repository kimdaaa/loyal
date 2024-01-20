from os import system
from player_stats import PlayerStats
from rank import Rank
from rpc import Rpc
from content import Content
from Request1 import Requests
from States.coregame import Coregame
from States.menu import Menu
from States.pregame import Pregame
from utils import utilities
from presence import Presences
import time
system('cls') 
system(f"title Loyal v1")

Requests = Requests()
presences = Presences(Requests,)
content = Content(Requests)
Pregame = Pregame(Requests)
menu = Menu(Requests, presences)
coregame = Coregame(Requests)
utilities = utilities(Requests)

from pathlib import Path
from tkinter import Tk, Canvas, Entry, Text, Button, PhotoImage
import tkinter as tk
import sys
from PIL import Image, ImageTk

OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / Path(r"C:\Users\i fucking hate windo\Desktop\Ur mum\frame0")




heartbeat_data = {
    "time": int(time.time()),
    "puuid": Requests.puuid,
    "players": {}
            }


class TextRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, text):
        self.text_widget.insert(tk.END, text)
        self.text_widget.see(tk.END)

def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)

def create_rounded_rectangle(canvas, x1, y1, x2, y2, radius, **kwargs):
    """Create a rounded rectangle on the canvas."""
    return canvas.create_polygon(
        x1 + radius, y1,
        x1 + radius, y1,
        x2 - radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1 + radius,
        x1, y1,
        x1 + radius, y1,
        smooth=True,
        **kwargs
    )

window = Tk()

window.geometry("800x389")

window.configure(bg = "#1A181B")

#title 
window.title("Loyal V1")

window.resizable(False, False)

# Set the path to the ICO file
ico_path = relative_to_assets('icon.ico')

# Convert the ICO file to a GIF file using Pillow
gif_path = ico_path.with_suffix('.gif')
Image.open(ico_path).save(gif_path)

# Create a PhotoImage object for the window icon
icon_image = ImageTk.PhotoImage(file=gif_path)

# Set the window icon
window.iconphoto(True, icon_image)


def Dodge():
    a = Pregame.get_pregame_match_id()
    print('[+] Game has been dodge lil ninja')
    utilities.dodge(a) 
def start_queue():
    a = menu.get_party_id(puuid=Requests.puuid)
    utilities.Queue(a)
    print('[+] queue has started retard')

canvas = Canvas(
    window,
    bg = "#1A181B",
    height = 389,
    width = 800,
    bd = 0,
    highlightthickness = 0,
    relief = "ridge"
)

canvas.place(x = 0, y = 0)
rounded_rectangle = create_rounded_rectangle(canvas, 10, 10, 790, 379, 20,
                                              fill="#000000",
                                                outline="")

button_image_1 = PhotoImage(
    file=relative_to_assets("button_1.png"))
button_1 = Button(
    image=button_image_1,
    borderwidth=0,
    highlightthickness=0,
    command= Dodge ,
    relief="flat",
)
button_1.place(
    x=630.0,
    y=304.0,
    width=131.0,
    height=37.0
)

button_image_2 = PhotoImage(
    file=relative_to_assets("button_2.png"))
button_2 = Button(
    image=button_image_2,
    borderwidth=0,
    highlightthickness=0,
    command= start_queue,
    relief="flat"
)
button_2.place(
    x=630.0,
    y=267.0,
    width=131.0,
    height=37.0
)

button_image_3 = PhotoImage(
    file=relative_to_assets("button_3.png"))
button_3 = Button(
    image=button_image_3,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("button_3 clicked"),
    relief="flat"
)
button_3.place(
    x=630.0,
    y=341.0,
    width=131.0,
    height=37.0
)

image_image_1 = PhotoImage(
    file=relative_to_assets("image_1.png"))
image_1 = canvas.create_image(
    91.0,
    83.0,
    image=image_image_1
)

image_image_2 = PhotoImage(
    file=relative_to_assets("image_2.png"))
image_2 = canvas.create_image(
    537.0,
    83.0,
    image=image_image_2
)

image_image_3 = PhotoImage(
    file=relative_to_assets("image_3.png"))
image_3 = canvas.create_image(
    684.0,
    83.0,
    image=image_image_3
)

image_image_4 = PhotoImage(
    file=relative_to_assets("image_4.png"))
image_4 = canvas.create_image(
    243.0,
    83.0,
    image=image_image_4
)

image_image_5 = PhotoImage(
    file=relative_to_assets("image_5.png"))
image_5 = canvas.create_image(
    390.0,
    83.0,
    image=image_image_5
)

canvas.create_rectangle(
    463.0,
    2.0,
    464.0,
    270.0,
    fill="#FFFFFF",
    outline="")

canvas.create_rectangle(
    315.0,
    -1.0,
    316.0,
    267.0,
    fill="#FFFFFF",
    outline="")

canvas.create_rectangle(
    164.0,
    5.0,
    165.0,
    273.0,
    fill="#FFFFFF",
    outline="")

canvas.create_rectangle(
    609.5,
    -1.0,
    610.5,
    267.0,
    fill="#FFFFFF",
    outline="")



    
entry_1 = Text(
    bd=2,
    bg="#000716",
    fg="#3E5D65",
    highlightthickness=0,

)
entry_1.place(
    x=39.0,
    y=267.0,
    width=571.0,
    height=109.0
)
sys.stdout = TextRedirector(entry_1)


window.mainloop()


#figd_AiXeu6V-xyMyEBY1lpCMcw40OYi0MBpXPZuPiepx
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
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
        x1 + radius, y1,
        smooth=True,
        **kwargs
    )

window = Tk()
window.geometry("770x389")
window.configure(bg = "#1A181B")
window.title("Loyal V1")
window.resizable(False, False)
ico_path = relative_to_assets('icon.ico')
gif_path = ico_path.with_suffix('.gif')
Image.open(ico_path).save(gif_path)
icon_image = ImageTk.PhotoImage(file=gif_path)
window.iconphoto(True, icon_image)


def Dodge():
    a = Pregame.get_pregame_match_id()
    print('[+] Game has been dodge lil NIGGER')
    utilities.dodge(a) 
    
def start_queue():
    a = menu.get_party_id(puuid=Requests.puuid)
    utilities.Queue(a)
    print('[+] queue has started retard')

def soloexP():
    print("[!] Timer (5.5s)")
    time.sleep(5.5)
    b = Pregame.Hover()
    print(b)

canvas = Canvas(
    window,
    bg = "#1A181B",
    height = 389,
    width = 770,
    bd = 0,
    highlightthickness = 0,
    relief = "ridge"
)

canvas.place(x = 0, y = 0)
rounded_rectangle = create_rounded_rectangle(canvas, 10, 10, 760, 379, 20, fill="#000000", outline="")

#boxes for data
canvas.create_rectangle(
    340.0,
    60.0,
    440.0,
    254.0,
    fill="#b0afb4",
    outline="")

canvas.create_rectangle(
    492.0,
    61.0,
    592.0,
    256.0,
    fill="#b0afb4",
    outline="")

canvas.create_rectangle(
    640.0,
    61.0,
    740.0,
    256.0,
    fill="#b0afb4",
    outline="")

canvas.create_rectangle(
    41.0,
    60.0,
    141.0,
    254.0,
    fill="#b0afb4",
    outline="")

canvas.create_rectangle(
    189.0,
    60.0,
    289.0,
    254.5,
    fill="#b0afb4",
    outline="")




#lines
canvas.create_rectangle(
    615.0,
    50,
    616.0,
    379.0,
    fill="#53d07a",
    outline="")

canvas.create_rectangle(
    164.0,
    50,
    165.0,
    267.0,
    fill="#53d07a",
    outline="")

canvas.create_rectangle(
    10,
    50.0,
    760.0,
    50.0,
    fill="#53d07a",
    outline="")

canvas.create_rectangle(
    315.0,
    50,
    316.0,
    267.0,
    fill="#53d07a",
    outline="")
canvas.create_rectangle(
    464.0,
    50.0,
    465.5,
    266.9999694824219,
    fill="#53d07a",
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


#ign boxes
canvas.create_rectangle(
    30.0,
    10.0,
    150.0,
    40.0,
    fill="#5e859b",
    outline="")

canvas.create_rectangle(
    180.0,
    10.0,
    300.0,
    40.0,
    fill="#5e859b",
    outline="")

canvas.create_rectangle(
    331.0,
    10.0,
    451.0,
    40.0,
    fill="#5e859b",
    outline="")

canvas.create_rectangle(
    482.0,
    10.0,
    602.0,
    40.0,
    fill="#5e859b",
    outline="")

canvas.create_rectangle(
    630.0,
    10.0,
    750.0,
    40.0,
    fill="#5e859b",
    outline="")

canvas.create_text(
    30.0,
    10.0,
    anchor="nw",
    text="tt",
    fill="#FFFFFF",
    font=("Inter", 12 * -1)
)

canvas.create_text(
    180.0,
    10.0,
    anchor="nw",
    text="tt",
    fill="#FFFFFF",
    font=("Inter", 12 * -1)
)

canvas.create_text(
    630.0,
    9.0,
    anchor="nw",
    text="tt",
    fill="#1A181B",
    font=("Inter", 12 * -1)
)

canvas.create_text(
    331.0,
    10.0,
    anchor="nw",
    text="tt",
    fill="#1A181B",
    font=("Inter", 12 * -1)
)

canvas.create_text(
    482.0,
    10.0,
    anchor="nw",
    text="tt",
    fill="#1A181B",
    font=("Inter", 12 * -1)
)

canvas.create_text(
    492.0,
    61.0,
    anchor="nw",
    text="t",
    fill="#000000",
    font=("Inter", 12 * -1)
)

canvas.create_text(
    42.0,
    59.0,
    anchor="nw",
    text="tRT",
    fill="#1A181B",
    font=("Inter", 12 * -1)
)

canvas.create_text(
    640.0,
    61.0,
    anchor="nw",
    text="tWT",
    fill="#000000",
    font=("Inter", 12 * -1)
)

canvas.create_text(
    340.0,
    60.0,
    anchor="nw",
    text="tTVBRasdasdadsasdasdadadsdaaaaaaaaaaaaaaaaa",
    fill="#000000",
    font=("Inter", 12 * -1)
)

canvas.create_text(
    189.0,
    60.0,
    anchor="nw",
    text="tASD",
    fill="#000000",
    font=("Inter", 12 * -1)
)
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
    x=625.0,
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
    x=625.0,
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
    command=soloexP,
    relief="flat"
)
button_3.place(
    x=625.0,
    y=341.0,
    width=131.0,
    height=37.0
)



#sys.stdout = TextRedirector(entry_1)


window.mainloop()


#figd_AiXeu6V-xyMyEBY1lpCMcw40OYi0MBpXPZuPiepx
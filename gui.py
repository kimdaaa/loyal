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


heartbeat_data = {
    "time": int(time.time()),
    "puuid": Requests.puuid,
    "players": {}
            }
puuid = Requests.puuid
party_id = menu.get_party_id(puuid)
response = Requests.fetch('glz', f'/session/v1/sessions/{puuid}', 'get')

import tkinter as tk

def main():
    window = tk.Tk()
    window.geometry("770x389")
    window.title("Line Drawing Test")

    canvas = tk.Canvas(window, height=400, width=800)
    canvas.pack()

    # Adjusting the use of create_line for drawing lines
    line_positions = [
        (615, 50, 615, 379),  # Line from (615, 50) to (615, 379)
        (164, 50, 164, 267),  # Adjusted for uniform length
        (315, 50, 315, 267),  # Adjusted for uniform length
        (464, 50, 464, 267),  # Adjusted for uniform length
        (10, 50, 760, 50),    # Horizontal line from (10, 50) to (760, 50)
    ]
    color = "#53d07a"  # Desired color for all lines

    for line in line_positions:
        # Create each line with specified color and width
        canvas.create_line(*line, fill=color, width=2)

    window.mainloop()

if __name__ == "__main__":
    main()
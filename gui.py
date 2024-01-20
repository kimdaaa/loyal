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

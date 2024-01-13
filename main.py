import presence
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
content = Content(Requests)
Pregame = Pregame(Requests)
utilities = utilities(Requests)

if __name__ == "__main__":
    a = Pregame.get_pregame_match_id()
    print(a)
    utilities.dodge(a)



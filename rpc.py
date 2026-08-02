from pypresence import Presence
from pypresence.exceptions import DiscordNotFound, InvalidID
import nest_asyncio
import time

class Rpc():
    def __init__(self, map_dict, gamemodes, colors, log):
        nest_asyncio.apply()
        self.discord_running = True
        try:
            self.rpc = Presence("1194467973214244894")
            self.rpc.connect()
            print("Connected to discord")
        except DiscordNotFound:
            print("Failed connecting to discord")
            self.discord_running = False
        self.gamemodes = gamemodes
        self.map_dict = map_dict
        self.data = {
            "agent": None,
            "rank": None,
            "rank_name": None
        }
        self.last_presence_data = {}
        self.colors = colors
        self.start_time = time.time()

    def set_data(self, data):
        self.data = self.data | data
        print("New data set in RPC")
        self.set_rpc(self.last_presence_data)

    @staticmethod
    def _match_field(presence, key, default=None):
        # Riot moved several fields (sessionLoopState, matchMap, ...) under
        # matchPresenceData at some point; fall back to top-level in case
        # that ever reverts or a field wasn't actually moved.
        match_data = presence.get("matchPresenceData") or {}
        if key in match_data:
            return match_data[key]
        return presence.get(key, default)

    @staticmethod
    def _party_field(presence, key, default=None):
        # partyAccessibility/partyState similarly live under partyPresenceData now.
        party_data = presence.get("partyPresenceData") or {}
        if key in party_data:
            return party_data[key]
        return presence.get(key, default)

    def set_rpc(self, presence):
        if not presence:
            return
        if self.discord_running:
            try:
                if presence.get("isValid"):
                    session_state = self._match_field(presence, "sessionLoopState")
                    if session_state == "INGAME":
                        if self.data.get("agent") is None or self.data.get("agent") == "":
                            agent_img = None
                            agent = None
                        else:
                            agent = self.colors.agent_dict.get(self.data.get("agent").lower())
                            agent_img = agent.lower().replace("/", "") if agent else None

                        if self._match_field(presence, "provisioningFlow") == "CustomGame":
                            gamemode = "Custom Game"
                        else:
                            gamemode = self.gamemodes.get(self._match_field(presence, "queueId"))

                        details = f"{gamemode} // {presence.get('partyOwnerMatchScoreAllyTeam')} - {presence.get('partyOwnerMatchScoreEnemyTeam')}"

                        match_map = self._match_field(presence, "matchMap") or ""
                        mapText = self.map_dict.get(match_map.lower())
                        if mapText == "The Range":
                            mapImage = "range"
                            details = "in Range"
                            agent_img = str(self.data.get("rank"))
                            agent = self.data.get("rank_name")
                        else:
                            mapImage = f"splash_{self.map_dict.get(match_map.lower())}_square".lower()
                        if mapText is None or mapText == "":
                            mapText = None
                            mapImage = None

                        if self._match_field(self.last_presence_data, "sessionLoopState") != session_state:
                            self.start_time = time.time()

                        self.rpc.update(
                            state=f"In a Party ({presence.get('partySize')} of {presence.get('maxPartySize')})",
                            details=details,
                            large_text=mapText,
                            large_image=agent_img,
                            small_text=agent,
                            start=self.start_time,
                            buttons=[{"label": "loyal", "url": "https://www.youtube.com/watch?v=Qr9EVULUGJs&list=RDQr9EVULUGJs&start_radio=1"}]
                        )
                        print("RPC in-game data update")

                    elif session_state == "MENUS":
                        if presence.get("isIdle"):
                            image = "game_icon_yellow"
                            image_text = "VALORANT - Idle"
                        else:
                            image = "game_icon"
                            image_text = "VALORANT - Online"

                        if self._party_field(presence, "partyAccessibility") == "OPEN":
                            party_string = "Open Party"
                        else:
                            party_string = "Closed Party"

                        if self._party_field(presence, "partyState") == "CUSTOM_GAME_SETUP":
                            gamemode = "Custom Game"
                        else:
                            gamemode = self.gamemodes.get(self._match_field(presence, "queueId"))

                        self.rpc.update(
                            state=f"{party_string} ({presence.get('partySize')} of {presence.get('maxPartySize')})",
                            details=f" Lobby - {gamemode}",
                            large_image=image,
                            large_text=image_text,
                            small_image=str(self.data.get("rank")),
                            small_text=self.data.get("rank_name"),
                            buttons=[{"label": "What's this? 👀", "url": "https://zaykenyon.github.io/VALORANT-rank-yoinker/"}]
                        )

            except InvalidID:
                self.discord_running = False
        else:
            try:
                self.rpc = Presence("1012402211134910546")
                self.rpc.connect()
                self.discord_running = True
                self.log("Reconnected to discord")
                self.set_rpc(presence)
            except DiscordNotFound:
                self.discord_running = False
        self.last_presence_data = presence

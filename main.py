from os import system
import os
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
import stats
import urllib3
import time
from pathlib import Path
from tkinter import Tk, Canvas, Entry, Text, Button, PhotoImage
import tkinter as tk
import sys
from PIL import Image, ImageTk

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ValorantRankYoinker:
    def __init__(self):
        self.first_time = True
        self.last_game_state = ""
        self.log = self.logging.log
        self.chat_log = self.chat_logging.chatLog
        self.presences = Presences(Requests, self.log)
        self.content = Content(Requests, self.log)
        self.rank = Rank(Requests, self.log, self.content, before_ascendant_seasons)
        self.pstats = PlayerStats(Requests, self.log, self.cfg)
        self.names = Names(Requests, self.log)
        self.coregame = Coregame(Requests, self.log)
        self.menu = Menu(Requests, self.log, self.presences)
        self.pregame = Pregame(Requests, self.log)
        self.rpc = Rpc(map_urls, gamemodes, Colors(hide_names, self.content.get_all_agents(), AGENTCOLORLIST), self.log) if self.cfg.get_feature_flag("discord_rpc") else None

    def main_loop(self):
        while True:
            try:
                presence = self.presences.get_presence()
                game_state = self.get_game_state(presence)
                if game_state:
                    self.log(f"Game state: {game_state}")
                    if game_state == "INGAME":
                        self.handle_ingame_state()
                    elif game_state == "PREGAME":
                        self.handle_pregame_state()
                    elif game_state == "MENUS":
                        self.handle_menus_state()
            except KeyboardInterrupt:
                os._exit(0)
            except Exception as e:
                self.handle_exception(e)

    def get_game_state(self, presence):
        if self.first_time:
            while True:
                presence = self.presences.get_presence()
                if self.presences.get_private_presence(presence):
                    break
                time.sleep(5)
            if self.cfg.get_feature_flag("discord_rpc"):
                self.rpc.set_rpc(self.presences.get_private_presence(presence))
            game_state = self.presences.get_game_state(presence)
            self.first_time = False
        else:
            game_state = self.presences.get_game_state(presence)
        return game_state

    def handle_ingame_state(self):
        coregame_stats = self.coregame.get_coregame_stats()
        if not coregame_stats:
            return

        Players = coregame_stats["Players"]
        presence = self.presences.get_presence()
        partyMembersList = [a["Subject"] for a in self.menu.get_party_members(Requests.puuid, presence)]
        players_data = {"ignore": partyMembersList}

        for player in Players:
            players_data.update({player["Subject"]: {"team": player["TeamID"], "agent": player["CharacterID"], "streamer_mode": player["PlayerIdentity"]["Incognito"]}})
        
        try:
            server = GAMEPODS[coregame_stats["GamePodID"]]
        except KeyError:
            server = "New server"
        
        self.presences.wait_for_presence(self.names.get_players_puuid(Players))
        names = self.names.get_names_from_puuids(Players)
        loadouts_arr = Loadouts(Requests, self.log, Colors(hide_names, self.content.get_all_agents(), AGENTCOLORLIST), server, self.coregame.get_current_map()).get_match_loadouts(self.coregame.get_coregame_match_id(), Players, self.cfg.weapon, requests.get("https://valorant-api.com/v1/weapons/skins").json(), names, state="game")
        loadouts = loadouts_arr[0]
        loadouts_data = loadouts_arr[1]

        playersLoaded = 1
        with self.console.status("Loading Players...") as status:
            partyOBJ = self.menu.get_party_json(self.names.get_players_puuid(Players), presence)
            Players.sort(key=lambda Players: Players["PlayerIdentity"].get("AccountLevel"), reverse=True)
            Players.sort(key=lambda Players: Players["TeamID"], reverse=True)
            partyCount = 0
            partyIcons = {}
            lastTeamBoolean = False
            lastTeam = "Red"
            already_played_with = []
            stats_data = self.pstats.read_data()

            for p in Players:
                if p["Subject"] == Requests.puuid:
                    allyTeam = p["TeamID"]
            for player in Players:
                status.update(f"Loading players... [{playersLoaded}/{len(Players)}]")
                playersLoaded += 1

                if player["Subject"] in stats_data.keys():
                    if player["Subject"] != Requests.puuid and player["Subject"] not in partyMembersList:
                        curr_player_stat = stats_data[player["Subject"]][-1]
                        i = 1
                        while curr_player_stat["match_id"] == self.coregame.match_id and len(stats_data[player["Subject"]]) > i:
                            i += 1
                        curr_player_stat = stats_data[player["Subject"]][-i]
                        if curr_player_stat["match_id"] != self.coregame.match_id:
                            times = 0
                            m_set = ()
                            for m in stats_data[player["Subject"]]:
                                if m["match_id"] != self.coregame.match_id and m["match_id"] not in m_set:
                                    times += 1
                                    m_set += (m["match_id"],)
                            if not player["PlayerIdentity"]["Incognito"]:
                                already_played_with.append({
                                    "times": times,
                                    "name": curr_player_stat["name"],
                                    "agent": curr_player_stat["agent"],
                                    "time_diff": time.time() - curr_player_stat["epoch"]
                                })
                            else:
                                team_string = "your" if player["TeamID"] == allyTeam else "enemy"
                                already_played_with.append({
                                    "times": times,
                                    "name": Colors(hide_names, self.content.get_all_agents(), AGENTCOLORLIST).escape_ansi(agent_dict[player["CharacterID"].lower()]) + " on " + team_string + " team",
                                    "agent": curr_player_stat["agent"],
                                    "time_diff": time.time() - curr_player_stat["epoch"]
                                })

                party_icon = ''
                if player["Subject"] == Requests.puuid:
                    if self.cfg.get_feature_flag("discord_rpc"):
                        self.rpc.set_data({"rank": playerRank["rank"], "rank_name": Colors(hide_names, self.content.get_all_agents(), AGENTCOLORLIST).escape_ansi(NUMBERTORANKS[playerRank["rank"]]) + " | " + str(playerRank["rr"]) + "rr"})
                
                ppstats = self.pstats.get_stats(player["Subject"])
                hs = ppstats["hs"]
                kd = ppstats["kd"]
                player_level = player["PlayerIdentity"].get("AccountLevel")

                if player["PlayerIdentity"]["Incognito"]:
                    Namecolor = Colors(hide_names, self.content.get_all_agents(), AGENTCOLORLIST).get_color_from_team(player["TeamID"], names[player["Subject"]], player["Subject"], Requests.puuid, agent=player["CharacterID"], party_members=partyMembersList)
                else:
                    Namecolor = Colors(hide_names, self.content.get_all_agents(), AGENTCOLORLIST).get_color_from_team(player["TeamID"], names[player["Subject"]], player["Subject"], Requests.puuid, party_members=partyMembersList)

                if lastTeam != player["TeamID"]:
                    lastTeamBoolean = True
                lastTeam = player['TeamID']
                if player["PlayerIdentity"]["HideAccountLevel"]:
                    PLcolor = Colors(hide_names, self.content.get_all_agents(), AGENTCOLORLIST).level_to_color(player_level) if player["Subject"] == Requests.puuid or player["Subject"] in partyMembersList or hide_levels == False else ""
                else:
                    PLcolor = Colors(hide_names, self.content.get_all_agents(), AGENTCOLORLIST).level_to_color(player_level)

                agent = Colors(hide_names, self.content.get_all_agents(), AGENTCOLORLIST).get_agent_from_uuid(player["CharacterID"].lower())
                name = Namecolor
                skin = loadouts[player["Subject"]]
                rankName = NUMBERTORANKS[playerRank["rank"]]
                if self.cfg.get_feature_flag("aggregate_rank_rr") and self.cfg.table.get("rr"):
                    rankName += f" ({playerRank['rr']})"
                rr = playerRank["rr"]
                peakRankAct = f" (e{playerRank['peakrankep']}a{playerRank['peakrankact']})"
                if not self.cfg.get_feature_flag("peak_rank_act"):
                    peakRankAct = ""
                peakRank = NUMBERTORANKS[playerRank["peakrank"]] + peakRankAct
                previousRank = NUMBERTORANKS[previousPlayerRank["rank"]]
                leaderboard = playerRank["leaderboard"]
                hs = Colors(hide_names, self.content.get_all_agents(), AGENTCOLORLIST).get_hs_gradient(hs)
                wr = Colors(hide_names, self.content.get_all_agents(), AGENTCOLORLIST).get_wr_gradient(playerRank["wr"]) + f" ({playerRank['numberofgames']})"

                self.pstats.save_data({
                    player["Subject"]: {
                        "name": names[player["Subject"]],
                        "agent": agent_dict[player["CharacterID"].lower()],
                        "map": self.coregame.get_current_map(map_urls, map_splashes),
                        "rank": playerRank["rank"],
                        "rr": rr,
                        "match_id": self.coregame.match_id,
                        "epoch": time.time(),
                    }
                })
        
        if self.cfg.get_feature_flag("last_played"):
            if len(already_played_with) > 0:
                for played in already_played_with:
                    self.console.print(f"Already played with {played['name']} (last {played['agent']}) {self.pstats.convert_time(played['time_diff'])} ago. (Total played {played['times']} times)")
                    self.chat_log(f"Already played with {played['name']} (last {played['agent']}) {self.pstats.convert_time(played['time_diff'])} ago. (Total played {played['times']} times)")
            already_played_with = []

    def handle_pregame_state(self):
        pregame_stats = self.pregame.get_pregame_stats()
        if not pregame_stats:
            return

        Players = pregame_stats["AllyTeam"]["Players"]
        self.presences.wait_for_presence(self.names.get_players_puuid(Players))
        names = self.names.get_names_from_puuids(Players)
        playersLoaded = 1

        with self.console.status("Loading Players...") as status:
            presence = self.presences.get_presence()
            partyOBJ = self.menu.get_party_json(self.names.get_players_puuid(Players), presence)
            partyMembersList = [a["Subject"] for a in self.menu.get_party_members(Requests.puuid, presence)]
            Players.sort(key=lambda Players: Players["PlayerIdentity"].get("AccountLevel"), reverse=True)
            partyCount = 0
            partyIcons = {}

            for player in Players:
                status.update(f"Loading players... [{playersLoaded}/{len(Players)}]")
                playersLoaded += 1

                party_icon = ''
                for party in partyOBJ:
                    if player["Subject"] in partyOBJ[party]:
                        if party not in partyIcons:
                            partyIcons.update({party: PARTYICONLIST[partyCount]})
                            party_icon = PARTYICONLIST[partyCount]
                            partyNum = partyCount + 1
                        else:
                            party_icon = partyIcons[party]
                        partyCount += 1
                playerRank = self.rank.get_rank(player["Subject"], seasonID)
                previousPlayerRank = self.rank.get_rank(player["Subject"], previousSeasonID)

                if player["Subject"] == Requests.puuid:
                    if self.cfg.get_feature_flag("discord_rpc"):
                        self.rpc.set_data({"rank": playerRank["rank"], "rank_name": Colors(hide_names, self.content.get_all_agents(), AGENTCOLORLIST).escape_ansi(NUMBERTORANKS[playerRank["rank"]]) + " | " + str(playerRank["rr"]) + "rr"})
                
                ppstats = self.pstats.get_stats(player["Subject"])
                hs = ppstats["hs"]
                kd = ppstats["kd"]
                player_level = player["PlayerIdentity"].get("AccountLevel")

                if player["PlayerIdentity"]["Incognito"]:
                    NameColor = Colors(hide_names, self.content.get_all_agents(), AGENTCOLORLIST).get_color_from_team(pregame_stats['Teams'][0]['TeamID'], names[player["Subject"]], player["Subject"], Requests.puuid, agent=player["CharacterID"], party_members=partyMembersList)
                else:
                    NameColor = Colors(hide_names, self.content.get_all_agents(), AGENTCOLORLIST).get_color_from_team(pregame_stats['Teams'][0]['TeamID'], names[player["Subject"]], player["Subject"], Requests.puuid, party_members=partyMembersList)

                if player["PlayerIdentity"]["HideAccountLevel"]:
                    PLcolor = Colors(hide_names, self.content.get_all_agents(), AGENTCOLORLIST).level_to_color(player_level) if player["Subject"] == Requests.puuid or player["Subject"] in partyMembersList or hide_levels == False else ""
                else:
                    PLcolor = Colors(hide_names, self.content.get_all_agents(), AGENTCOLORLIST).level_to_color(player_level)
                
                if player["CharacterSelectionState"] == "locked":
                    agent_color = color(str(agent_dict.get(player["CharacterID"].lower())), fore=(255, 255, 255))
                elif player["CharacterSelectionState"] == "selected":
                    agent_color = color(str(agent_dict.get(player["CharacterID"].lower())), fore=(128, 128, 128))
                else:
                    agent_color = color(str(agent_dict.get(player["CharacterID"].lower())), fore=(54, 53, 51))

                agent = agent_color
                name = NameColor
                rankName = NUMBERTORANKS[playerRank["rank"]]
                if self.cfg.get_feature_flag("aggregate_rank_rr") and self.cfg.table.get("rr"):
                    rankName += f" ({playerRank['rr']})"
                rr = playerRank["rr"]
                peakRankAct = f" (e{playerRank['peakrankep']}a{playerRank['peakrankact']})"
                if not self.cfg.get_feature_flag("peak_rank_act"):
                    peakRankAct = ""
                peakRank = NUMBERTORANKS[playerRank["peakrank"]] + peakRankAct
                previousRank = NUMBERTORANKS[previousPlayerRank["rank"]]
                leaderboard = playerRank["leaderboard"]
                hs = Colors(hide_names, self.content.get_all_agents(), AGENTCOLORLIST).get_hs_gradient(hs)
                wr = Colors(hide_names, self.content.get_all_agents(), AGENTCOLORLIST).get_wr_gradient(playerRank["wr"]) + f" ({playerRank['numberofgames']})"

    def handle_menus_state(self):
        Players = self.menu.get_party_members(Requests.puuid, self.presences.get_presence())
        names = self.names.get_names_from_puuids(Players)
        playersLoaded = 1

        with self.console.status("Loading Players...") as status:
            Players.sort(key=lambda Players: Players["PlayerIdentity"].get("AccountLevel"), reverse=True)
            seen = []
            for player in Players:
                if player not in seen:
                    status.update(f"Loading players... [{playersLoaded}/{len(Players)}]")
                    playersLoaded += 1
                    party_icon = PARTYICONLIST[0]
                    playerRank = self.rank.get_rank(player["Subject"], seasonID)
                    previousPlayerRank = self.rank.get_rank(player["Subject"], previousSeasonID)

                    if player["Subject"] == Requests.puuid:
                        if self.cfg.get_feature_flag("discord_rpc"):
                            self.rpc.set_data({"rank": playerRank["rank"], "rank_name": Colors(hide_names, self.content.get_all_agents(), AGENTCOLORLIST).escape_ansi(NUMBERTORANKS[playerRank["rank"]]) + " | " + str(playerRank["rr"]) + "rr"})
                    
                    ppstats = self.pstats.get_stats(player["Subject"])
                    hs = ppstats["hs"]
                    kd = ppstats["kd"]
                    player_level = player["PlayerIdentity"].get("AccountLevel")
                    PLcolor = Colors(hide_names, self.content.get_all_agents(), AGENTCOLORLIST).level_to_color(player_level)

                    agent = ""
                    name = color(names[player["Subject"]], fore=(76, 151, 237))
                    rankName = NUMBERTORANKS[playerRank["rank"]]
                    if self.cfg.get_feature_flag("aggregate_rank_rr") and self.cfg.table.get("rr"):
                        rankName += f" ({playerRank['rr']})"
                    rr = playerRank["rr"]
                    peakRankAct = f" (e{playerRank['peakrankep']}a{playerRank['peakrankact']})"
                    if not self.cfg.get_feature_flag("peak_rank_act"):
                        peakRankAct = ""
                    peakRank = NUMBERTORANKS[playerRank["peakrank"]] + peakRankAct
                    previousRank = NUMBERTORANKS[previousPlayerRank["rank"]]
                    leaderboard = playerRank["leaderboard"]
                    hs = Colors(hide_names, self.content.get_all_agents(), AGENTCOLORLIST).get_hs_gradient(hs)
                    wr = Colors(hide_names, self.content.get_all_agents(), AGENTCOLORLIST).get_wr_gradient(playerRank["wr"]) + f" ({playerRank['numberofgames']})"

                    seen.append(player["Subject"])


if __name__ == "__main__":
    valo_rank_yoinker = ValorantRankYoinker()
    valo_rank_yoinker.start()

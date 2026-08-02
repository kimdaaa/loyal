import asyncio
import os
import socket
import sys
import time
import traceback
import threading
import types
import urllib3
import json
import base64
import random # Added for simulation randomness

# Import the GUI class (used for type hinting, actual import for run is in main.py)
# Note: Do NOT directly run app_backend.py, it's meant to be imported by gui.py/main.py
from gui import ValorantYoinkerGUI

# Core backend classes that are retained based on your project files
from player_stats import PlayerStats
from rank import Rank
from content import Content
from Request1 import Requests # Assuming Request1.py contains the Requests CLASS
from States.coregame import Coregame
from States.menu import Menu
from States.pregame import Pregame # Import Pregame
from names import Names
from presence import Presences
from presence import Stats
from player_format import format_player_entry
from skins import Skins
from rpc import Rpc

# --- IMPORTING CONSTANTS FROM constants.py ---
from constants import (
    version,
    tierDict, AGENTCOLORLIST,
    sockets, characters,
    before_ascendant_seasons, DEFAULT_CONFIG, gamemodes
)

import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

server = ""

def program_exit(status: int):
    sys.exit(status)

class ValorantRankYoinker:
    def __init__(self, status_callback=None):
        # status_callback lets a caller (e.g. main.py, before the GUI has attached
        # this backend) receive log messages emitted during __init__ itself --
        # including the lockfile-wait retry loop below, which can block for a long
        # time if Valorant/Riot Client isn't running yet.
        self.log_gui_callback = status_callback
        self._current_players_data = []
        self._played_with_players = []
        self._current_match_id = None # <-- ADDED: Initialize _current_match_id
        self._last_history_match_id = None
        self._game_state = None
        self._loop_iteration = 0 # Tracks poll cycles so we can refresh content periodically

        self.Requests = Requests(logger=self._log_to_status)
        self.content = Content(self.Requests, self._log_to_status)

        # Fetch content once at init so Rank has season/act data available immediately
        # in every game state (not just MENUS like before).
        initial_content = self.content.get_content()
        if not initial_content:
            self._log_to_status("Failed to fetch initial content data.", tag="error")

        self.rank = Rank(self.Requests, before_ascendant_seasons, self.content)
        self.player_stats = PlayerStats(self.Requests)
        self.names = Names(self.Requests)
        self.presences = Presences(self.Requests)
        self.stats = Stats()
        self.skins = Skins(self.Requests)

        self.menu_state = Menu(self.Requests, self.presences)
        self.pregame_state = Pregame(self.Requests, self.names, self.rank, self.player_stats, self.skins, self.presences, self.content)
        self.coregame_state = Coregame(self.Requests, self.names, self.rank, self.player_stats, self.skins, self.presences, self.content)

        # Discord Rich Presence is optional; never let failures here crash the app.
        self.rpc = None
        try:
            if DEFAULT_CONFIG.get("flags", {}).get("discord_rpc"):
                all_maps = self.content.get_all_maps()
                map_dict = self.content.get_map_urls(all_maps)
                agent_dict = self.content.get_all_agents()
                colors = types.SimpleNamespace(agent_dict=agent_dict)
                self.rpc = Rpc(map_dict, gamemodes, colors, self._log_to_status)
        except Exception as e:
            self._log_to_status(f"Failed to initialize Discord RPC: {e}", tag="warning")
            self.rpc = None

        self._stop_event = threading.Event()
        self._data_fetch_thread = threading.Thread(target=self._data_fetch_loop, daemon=True)
        self._data_fetch_thread.start()

        self._log_to_status("ValorantRankYoinker backend initialized.", tag="info")

    def _log_to_status(self, message, tag="info"):
        if self.log_gui_callback:
            self.log_gui_callback(message, tag)

    def _data_fetch_loop(self):
        while not self._stop_event.is_set():
            self._fetch_and_process_data()
            time.sleep(10)

    def _update_played_with(self, processed_players):
        if not processed_players:
            return []
        match_id = self._current_match_id
        save_this_poll = bool(match_id and match_id != self._last_history_match_id)
        puuids_this_match = {
            p["puuid"]: f"{p['name']}#{p['tag']}"
            for p in processed_players
            if p.get("puuid") and p["puuid"] != self.Requests.puuid
        }
        if not puuids_this_match:
            return []
        history = self.stats.read_data()
        already_played_with = []
        for puuid, label in puuids_this_match.items():
            prior_matches = {entry.get("match_id") for entry in history.get(puuid, []) if isinstance(entry, dict)}
            if match_id and match_id in prior_matches:
                continue
            prior_count = len(prior_matches) if prior_matches else len(history.get(puuid, []))
            if prior_count:
                already_played_with.append(f"{label} (played {prior_count}x before)")
        if save_this_poll:
            self.stats.save_data({puuid: {"label": label, "match_id": match_id} for puuid, label in puuids_this_match.items()})
            self._last_history_match_id = match_id
        return already_played_with

    def _fetch_and_process_data(self):
        try:
            presences = self.presences.get_presence()
            game_state = self.presences.get_game_state(presences)
            self._game_state = game_state

            if game_state not in ("MENUS", "PREGAME", "INGAME"):
                own_entries = [p for p in presences if p.get("puuid") == self.Requests.puuid]
                private_dump = "N/A"
                try:
                    private_presence_debug = self.presences.get_private_presence(presences)
                    if private_presence_debug is not None:
                        private_dump = repr(private_presence_debug)
                    else:
                        private_dump = "get_private_presence returned None"
                except Exception as e:
                    private_dump = f"get_private_presence raised: {e!r}"
                self._log_to_status(
                    "Debug: game_state unresolved. "
                    f"own_puuid={self.Requests.puuid!r} | "
                    f"{len(presences)} presences total | "
                    f"{len(own_entries)} entries match own puuid | "
                    f"own_entry_products={[p.get('product') for p in own_entries]!r} | "
                    f"decoded_private={private_dump}",
                    tag="debug",
                )

            # Refresh content periodically (~every 60s given the 10s poll interval),
            # regardless of game state, since Rank now needs Content in all states.
            self._loop_iteration += 1
            if self._loop_iteration % 6 == 0:
                refreshed_content = self.content.get_content()
                if not refreshed_content:
                    self._log_to_status("Failed to refresh content data.", tag="warning")

            private_presence = self.presences.get_private_presence(presences)

            if self.rpc and private_presence:
                try:
                    self.rpc.set_rpc(private_presence)
                except Exception as e:
                    self._log_to_status(f"Error updating Discord RPC: {e}", tag="warning")

            processed_players = []

            if game_state == "MENUS":
                self._log_to_status("In Menus...")
                self._current_match_id = None # Clear match ID when in menus
                my_party_id = private_presence.get("partyId") if private_presence else None

                content_snapshot = self.content.content
                current_season_id = None
                if content_snapshot:
                    current_season_id = self.content.get_latest_season_id(content_snapshot)

                if not current_season_id:
                    self._log_to_status("Could not determine current season ID. Rank data may be incomplete.", tag="error")
                    self._current_players_data = []
                    self._played_with_players = []
                    return

                party_map = self.presences.get_party_map(presences)
                party_indices = self.presences.assign_party_indices(party_map)

                party_members = []
                if my_party_id:
                    seen_party_puuids = set()
                    for presence in presences:
                        puuid = presence.get("puuid")
                        if not puuid or puuid in seen_party_puuids:
                            continue
                        if party_map.get(puuid) == my_party_id:
                            seen_party_puuids.add(puuid)
                            party_members.append(presence)

                for player_presence in party_members:
                    puuid = player_presence.get("puuid")
                    full_name = self.names.get_name_from_puuid(puuid)
                    if full_name and "#" in full_name:
                        name, tag = full_name.rsplit("#", 1)
                    else:
                        name, tag = (full_name or "Unknown"), ""

                    rank_data = self.rank.get_rank(puuid, current_season_id)
                    stats_data = self.player_stats.get_stats(puuid)
                    level = player_presence.get("PlayerIdentity", {}).get("AccountLevel", "N/A")

                    processed_players.append(format_player_entry(
                        puuid, name, tag, rank_data, stats_data, level,
                        agent="N/A (Menus)", skin="N/A",
                        party_index=party_indices.get(puuid), team="friendly"
                    ))

                self._log_to_status(f"Updated menu data for {len(processed_players)} party members.", tag="info")
                self._current_players_data = processed_players
                self._played_with_players = []
                return

            elif game_state == "PREGAME":
                self._log_to_status("In Pregame (Agent Select)...")
                pregame_data = self.pregame_state.get_pregame_data()
                self._current_match_id = pregame_data.get("MatchID")
                processed_players = pregame_data.get("players", [])
                self._played_with_players = self._update_played_with(processed_players)
                self._log_to_status(f"Updated pregame data for {len(processed_players)} players.", tag="info")

            elif game_state == "INGAME":
                self._log_to_status("In Game...")
                # NOTE: Do NOT clear _current_match_id here -- doing so breaks
                # dodge_game()/lock_agent() logic if called right after transitioning
                # out of pregame. Only MENUS and the error path clear it.
                coregame_data = self.coregame_state.get_coregame_data()
                processed_players = coregame_data.get("players", [])
                self._played_with_players = self._update_played_with(processed_players)
                self._log_to_status(f"Updated in-game data for {len(processed_players)} players.", tag="info")

            else:
                self._log_to_status("Game state unknown or not in game. Waiting...", tag="warning")
                self._current_match_id = None # Clear match ID if not in a recognized state
                self._played_with_players = []

            self._current_players_data = processed_players

        except Exception as e:
            self._log_to_status(f"Error fetching data: {e}", tag="error")
            self._current_players_data = []
            self._played_with_players = []
            self._current_match_id = None # Clear match ID on error

    def force_update_data_from_gui(self):
        self._log_to_status("Forcing data update from GUI...", tag="action")
        self._fetch_and_process_data()

    def dodge_game(self):
        self._log_to_status("Attempting to dodge game...", tag="action")
        try:
            # Use _current_match_id if available, otherwise try to fetch from pregame_state
            match_id_to_use = self._current_match_id
            if not match_id_to_use:
                # Fallback if _current_match_id wasn't set (e.g., if called too quickly)
                match_id_to_use = self.pregame_state.get_pregame_match_id()

            if match_id_to_use:
                dodge_response = self.Requests.fetch(url_type='glz', endpoint=f"/pregame/v1/matches/{match_id_to_use}/quit", method="post")
                dodge_ok = isinstance(dodge_response, dict) and "errorCode" not in dodge_response
                self._log_to_status("Game dodged successfully!" if dodge_ok else f"Failed to dodge game. Response: {dodge_response}", tag="success" if dodge_ok else "error")
            else:
                self._log_to_status("Not in a pre-game lobby to dodge.", tag="warning")
        except Exception as e:
            self._log_to_status(f"Error dodging game: {e}", tag="error")

    def start_queue(self):
        self._log_to_status("Attempting to start queue...", tag="action")
        try:
            party_id = self.menu_state.get_party_id(self.Requests.puuid)
            if party_id:
                queue_response = self.Requests.fetch(url_type='glz', endpoint=f"/parties/v1/parties/{party_id}/matchmaking/join", method="post")
                queue_ok = isinstance(queue_response, dict) and "errorCode" not in queue_response
                self._log_to_status("Queue started successfully!" if queue_ok else f"Failed to start queue. Response: {queue_response}", tag="success" if queue_ok else "error")
            else:
                self._log_to_status("Could not get party ID to start queue.", tag="warning")
        except Exception as e:
            self._log_to_status(f"Error starting queue: {e}", tag="error")

    def lock_agent(self, agent_name):
        """
        Attempts to lock a selected agent in the pre-game lobby using the provided Hover logic.
        """
        # Ensure we have a current match ID. This should be populated by _fetch_and_process_data.
        match_id_to_use = self._current_match_id
        if not match_id_to_use:
            # Fallback: try to fetch it directly from Pregame state if it wasn't set by the loop
            match_id_to_use = self.pregame_state.get_pregame_match_id()

        if not match_id_to_use:
            self._log_to_status("Not in an active pre-game match (agent select) to lock an agent.", tag="warning")
            return

        agent_uuid = None
        wanted = str(agent_name or "").strip().lower()
        for uuid, name in characters.items():
            if str(name or "").strip().lower() == wanted:
                agent_uuid = uuid
                agent_name = name
                break

        if not agent_uuid:
            self._log_to_status(f"Unknown agent '{agent_name}'. Cannot lock.", tag="error")
            return

        self._log_to_status(f"Attempting to select and lock {agent_name} (UUID: {agent_uuid})...", tag="action")
        try:
            select_response = self.Requests.fetch(
                url_type='glz',
                endpoint=f"/pregame/v1/matches/{match_id_to_use}/select/{agent_uuid}",
                method='post'
            )
            if isinstance(select_response, dict) and "errorCode" in select_response:
                self._log_to_status(f"Agent select returned: {select_response}", tag="warning")

            lock_response = self.Requests.fetch(
                url_type='glz',
                endpoint=f"/pregame/v1/matches/{match_id_to_use}/lock/{agent_uuid}",
                method='post'
            )

            lock_ok = isinstance(lock_response, dict) and "errorCode" not in lock_response
            if lock_ok:
                self._log_to_status(f"Successfully locked {agent_name}!", tag="success")
            else:
                self._log_to_status(f"Failed to lock {agent_name}. Response: {lock_response}", tag="error")
        except Exception as e:
            self._log_to_status(f"Error during agent lock for {agent_name}: {e}", tag="error")

    def get_current_players_data(self):
        return self._current_players_data

    def get_played_with_players_data(self):
        return self._played_with_players

    def get_current_players_data_for_ui(self):
        return self._current_players_data

    def get_played_with_players_for_ui(self):
        return self._played_with_players

    def get_game_state_for_ui(self):
        return getattr(self, "_game_state", None)

    def get_available_agents(self):
        try:
            raw_agent_names = list(characters.values())

            agent_names = []
            for name in raw_agent_names:
                if name is None:
                    self._log_to_status("Warning: Detected None in agent list from constants. Skipping.", tag="warning")
                    continue
                if not isinstance(name, str):
                    self._log_to_status(f"Warning: Detected non-string agent name '{name}' (type: {type(name)}). Skipping.", tag="warning")
                    continue
                agent_names.append(name)

            self._log_to_status(f"Fetched {len(agent_names)} valid agents from constants.", tag="debug")
            return sorted(agent_names)
        except Exception as e:
            self._log_to_status(f"Critical error loading or sorting available agents: {e}", tag="error")
            return []

    def __del__(self):
        if hasattr(self, '_stop_event') and self._stop_event:
            self._stop_event.set()
            if self._data_fetch_thread.is_alive():
                self._data_fetch_thread.join(timeout=5)

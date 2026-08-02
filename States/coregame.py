import time
import json  # Ensure json is imported for parsing if needed

from constants import characters
from player_format import format_player_entry


class Coregame:
    def __init__(self, Requests, names, rank, player_stats, skins, presences, content):
        self.Requests = Requests
        self.names = names
        self.rank = rank
        self.player_stats = player_stats
        self.skins = skins
        self.presences = presences
        self.content = content
        self.response = ""
        self._current_coregame_match_id = None  # Initialize internal match ID storage
        # Per-player rank/stats/skin don't change mid-match, so cache them keyed by
        # puuid for the lifetime of the current match instead of refetching every
        # 10s poll tick -- that refetching is what was tripping Riot's rate limits.
        self._enrichment_cache = {}
        self._cached_match_id = None
        self._match_skins_map = {}

    def get_coregame_match_id(self):
        """
        Fetches the current core game match ID for the current player (puuid).
        """
        try:
            response = self.Requests.fetch(url_type="glz",
                                           endpoint=f"/core-game/v1/players/{self.Requests.puuid}",
                                           method="get")

            if response and response.get("errorCode") == "RESOURCE_NOT_FOUND":
                self.Requests.logger("Not in a core game match (RESOURCE_NOT_FOUND).", tag="info")
                self._current_coregame_match_id = None
                return None # Return None or a falsy value to indicate no match

            if response and 'MatchID' in response:
                match_id = response['MatchID']
                self.Requests.logger(f"Retrieved coregame match ID: '{match_id}'", tag="debug")
                self._current_coregame_match_id = match_id
                if match_id != self._cached_match_id:
                    self._enrichment_cache = {}
                    self._cached_match_id = match_id
                    try:
                        self._match_skins_map = self.skins.get_match_skins(match_id, "coregame") if self.skins else {}
                    except Exception as e:
                        self.Requests.logger(f"Error fetching match skins: {e}", tag="warning")
                        self._match_skins_map = {}
                return match_id
            else:
                self.Requests.logger(f"No MatchID found in coregame player response. Response: {response}", tag="warning")
                self._current_coregame_match_id = None
                return None
        except (KeyError, TypeError, AttributeError) as e: # Added AttributeError for safety if response is not dict-like
            self.Requests.logger(f"Error finding coregame match ID: {e}. Response: {self.response}", tag="error")
            self._current_coregame_match_id = None
            return None

    def get_coregame_stats(self):
        """
        Fetches detailed core game statistics for the current match ID.
        This is an internal helper, get_coregame_data will call this.
        """
        if not self._current_coregame_match_id: # Use the internal ID, ensuring it's populated
            # Try to get it again, in case it was just updated or missed by get_coregame_data
            self.get_coregame_match_id()
            if not self._current_coregame_match_id:
                return None # No match ID available, cannot get stats

        match_id = self._current_coregame_match_id

        # Ensure 'glz' endpoint for core-game matches is correct
        # Based on Riot's API, it's usually /core-game/v1/matches/{match_id}
        response = self.Requests.fetch(url_type="glz",
                                       endpoint=f"/core-game/v1/matches/{match_id}",
                                       method="get")
        return response

    def _resolve_agent(self, agent_id):
        if not agent_id:
            return "N/A"
        return characters.get(agent_id.lower(), "N/A")

    def _enrich_player(self, puuid, agent_id, team, names_map, party_indices, current_season_id, level=None):
        """Builds one fully-enriched player entry. Any per-player enrichment
        failure falls back to graceful defaults via format_player_entry rather
        than dropping the player or crashing the whole match."""
        agent = self._resolve_agent(agent_id)

        name_tag = names_map.get(puuid) if names_map else None
        name, tag = None, None
        if name_tag:
            if "#" in name_tag:
                name, tag = name_tag.rsplit("#", 1)
            else:
                name = name_tag

        cached = self._enrichment_cache.get(puuid)
        if cached:
            rank_data = cached["rank_data"]
            stats_data = cached["stats_data"]
            skin = cached["skin"]
        else:
            rank_data = None
            try:
                if current_season_id:
                    rank_data = self.rank.get_rank(puuid, current_season_id)
            except Exception as e:
                self.Requests.logger(f"Error fetching rank for {puuid}: {e}", tag="warning")
                rank_data = None

            stats_data = None
            try:
                stats_data = self.player_stats.get_stats(puuid)
            except Exception as e:
                self.Requests.logger(f"Error fetching stats for {puuid}: {e}", tag="warning")
                stats_data = None

            skin = self._match_skins_map.get(puuid, "N/A")

            self._enrichment_cache[puuid] = {"rank_data": rank_data, "stats_data": stats_data, "skin": skin}

        try:
            return format_player_entry(
                puuid,
                name,
                tag,
                rank_data,
                stats_data,
                level=level,
                agent=agent,
                skin=skin,
                party_index=party_indices.get(puuid) if party_indices else None,
                team=team,
            )
        except Exception as e:
            self.Requests.logger(f"Error formatting player entry for {puuid}: {e}", tag="warning")
            return format_player_entry(puuid, name, tag, None, None, None, agent, "N/A", None, team)

    def get_coregame_data(self):
        """
        Combines match ID retrieval and stats fetching to return processed core game data
        in the format expected by app_backend.py.
        """
        # Ensure we have the latest match ID before fetching stats
        self._current_coregame_match_id = self.get_coregame_match_id()

        if not self._current_coregame_match_id:
            self.Requests.logger("Not in an active core game match.", tag="info")
            return {"MatchID": None, "players": []} # Return empty data

        coregame_stats = self.get_coregame_stats()

        if coregame_stats is None:
            self.Requests.logger(f"Failed to retrieve core game stats for match ID: {self._current_coregame_match_id}", tag="error")
            return {"MatchID": None, "players": []}

        # --- PARSE ACTUAL CORE GAME API RESPONSE HERE ---
        # The structure of `coregame_stats` depends entirely on the Valorant API's
        # `/core-game/v1/matches/{match_id}` endpoint. Two possible shapes are handled:
        #   Scenario 1: Players are directly in the top-level 'Players' list, each with 'TeamID'.
        #   Scenario 2: Players are nested under 'Teams' -> 'Players', with team id on the team.
        raw_players = []  # list of (puuid, agent_id, team_id, account_level)

        if "Players" in coregame_stats:
            for player_entry in coregame_stats["Players"]:
                puuid = player_entry.get("Subject")
                if not puuid:
                    continue
                raw_players.append((
                    puuid,
                    player_entry.get("CharacterID"),
                    player_entry.get("TeamID"),
                    (player_entry.get("PlayerIdentity") or {}).get("AccountLevel"),
                ))
        elif "Teams" in coregame_stats:
            for team in coregame_stats["Teams"]:
                team_id = team.get("ID")
                for player_entry in team.get("Players", []):
                    puuid = player_entry.get("Subject")
                    if not puuid:
                        continue
                    raw_players.append((
                        puuid,
                        player_entry.get("CharacterID"),
                        team_id,
                        (player_entry.get("PlayerIdentity") or {}).get("AccountLevel"),
                    ))

        # Determine the local player's team so everyone else can be classified
        # friendly/enemy relative to it.
        local_puuid = self.Requests.puuid
        local_team_id = None
        for puuid, _agent_id, team_id, _level in raw_players:
            if puuid == local_puuid:
                local_team_id = team_id
                break

        all_puuids = [p[0] for p in raw_players]

        # Bulk-resolve names for everyone in the match to minimize request count.
        try:
            names_map = self.names.get_multiple_names_from_puuid(all_puuids) if all_puuids else {}
        except Exception as e:
            self.Requests.logger(f"Error resolving names for coregame match: {e}", tag="warning")
            names_map = {}

        # Build party map for coloring parties in the GUI.
        try:
            presences_list = self.presences.get_presence()
            party_map = self.presences.get_party_map(presences_list)
            party_indices = self.presences.assign_party_indices(party_map)
        except Exception as e:
            self.Requests.logger(f"Error building party map for coregame match: {e}", tag="warning")
            party_indices = {}

        # Determine current season id for rank lookups.
        current_season_id = None
        try:
            if self.content and self.content.content:
                current_season_id = self.content.get_latest_season_id(self.content.content)
        except Exception as e:
            self.Requests.logger(f"Error determining current season id: {e}", tag="warning")
            current_season_id = None

        if not current_season_id:
            self.Requests.logger("No current season id available; skipping rank enrichment for this match.", tag="warning")

        processed_players = []
        for puuid, agent_id, team_id, level in raw_players:
            if local_team_id is not None:
                team = "friendly" if team_id == local_team_id else "enemy"
            else:
                # Could not determine local player's team (e.g. local player not
                # found in the player list) -- default everyone to friendly.
                team = "friendly"
            try:
                processed_players.append(self._enrich_player(
                    puuid, agent_id, team, names_map, party_indices, current_season_id, level
                ))
            except Exception as e:
                self.Requests.logger(f"Error enriching coregame player {puuid}: {e}", tag="warning")

        self.Requests.logger(f"Fetched {len(processed_players)} players from core game data.", tag="debug")

        return {
            "MatchID": self._current_coregame_match_id,
            "players": processed_players,
        }

    def get_current_map(self, map_urls, map_splashes) -> dict:
        """
        Abstracts get_coregame_stats() to get the current map name and splash.
        :return: Dictionary of appropriate name and splash.
        """
        coregame_stats = self.get_coregame_stats()

        if not coregame_stats or not coregame_stats.get("MapID"):
            return {'name': 'N/A', 'splash': 'N/A'}

        current_map_id = coregame_stats['MapID']

        # You need a way to map MapID to a display name and splash URL.
        # This usually comes from the 'content' endpoint or pre-defined constants.
        # Assuming map_urls and map_splashes are dictionaries mapped by canonical map names.
        map_name = "Unknown Map"
        for map_uuid, name in map_urls.items():  # Assuming map_urls is a UUID->Name mapping
            if map_uuid and map_uuid.lower() == current_map_id.lower():
                map_name = name
                break

        if map_name != "Unknown Map" and map_name in map_splashes:
            return {'name': map_name, 'splash': map_splashes[map_name]}
        else:
            return {'name': current_map_id, 'splash': 'N/A'}  # Fallback to ID if name/splash not found

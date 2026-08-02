import json  # You might need this for parsing API responses

from constants import characters
from player_format import format_player_entry


class Pregame:
    def __init__(self, requests_instance, names, rank, player_stats, skins, presences, content):
        self.requests = requests_instance  # This is your Requests object for API calls
        self.names = names
        self.rank = rank
        self.player_stats = player_stats
        self.skins = skins
        self.presences = presences
        self.content = content
        self._current_pregame_match_id = None  # Internal storage for the match ID
        # Per-player rank/stats/skin don't change mid-match, so cache them keyed by
        # puuid for the lifetime of the current match instead of refetching every
        # 10s poll tick -- that refetching is what was tripping Riot's rate limits.
        self._enrichment_cache = {}
        self._cached_match_id = None
        self._match_skins_map = {}

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
                self.requests.logger(f"Error fetching rank for {puuid}: {e}", tag="warning")
                rank_data = None

            stats_data = None
            try:
                stats_data = self.player_stats.get_stats(puuid)
            except Exception as e:
                self.requests.logger(f"Error fetching stats for {puuid}: {e}", tag="warning")
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
            self.requests.logger(f"Error formatting player entry for {puuid}: {e}", tag="warning")
            return format_player_entry(puuid, name, tag, None, None, None, agent, "N/A", None, team)

    def get_pregame_data(self):
        """
        Fetches the current pre-game match data from the Valorant API.
        This method is called by app_backend's _fetch_and_process_data.
        """
        try:
            # First, fetch the overall pre-game match status/ID
            response = self.requests.fetch('glz', "/pregame/v1/pregamematch", 'get')

            if response and response.get("ID"):  # Assuming the API response has an "ID" for the match
                match_id = response["ID"]
                self._current_pregame_match_id = match_id  # Store the ID

                if match_id != self._cached_match_id:
                    self._enrichment_cache = {}
                    self._cached_match_id = match_id
                    try:
                        self._match_skins_map = self.skins.get_match_skins(match_id, "pregame") if self.skins else {}
                    except Exception as e:
                        self.requests.logger(f"Error fetching match skins: {e}", tag="warning")
                        self._match_skins_map = {}

                # Now fetch detailed information about this specific match
                match_details = self.requests.fetch('glz', f"/pregame/v1/matches/{match_id}", 'get')

                if match_details:
                    ally_players = match_details.get("AllyTeam", {}).get("Players", []) or []
                    enemy_players = match_details.get("EnemyTeam", {}).get("Players", []) or []

                    all_puuids = [p.get("Subject") for p in ally_players + enemy_players if p.get("Subject")]

                    # Bulk-resolve names for everyone in the match to minimize request count.
                    try:
                        names_map = self.names.get_multiple_names_from_puuid(all_puuids) if all_puuids else {}
                    except Exception as e:
                        self.requests.logger(f"Error resolving names for pregame match: {e}", tag="warning")
                        names_map = {}

                    # Build party map for coloring parties in the GUI.
                    try:
                        presences_list = self.presences.get_presence()
                        party_map = self.presences.get_party_map(presences_list)
                        party_indices = self.presences.assign_party_indices(party_map)
                    except Exception as e:
                        self.requests.logger(f"Error building party map for pregame match: {e}", tag="warning")
                        party_indices = {}

                    # Determine current season id for rank lookups.
                    current_season_id = None
                    try:
                        if self.content and self.content.content:
                            current_season_id = self.content.get_latest_season_id(self.content.content)
                    except Exception as e:
                        self.requests.logger(f"Error determining current season id: {e}", tag="warning")
                        current_season_id = None

                    if not current_season_id:
                        self.requests.logger("No current season id available; skipping rank enrichment for this match.", tag="warning")

                    players_data = []
                    for player_entry in ally_players:
                        puuid = player_entry.get("Subject")
                        if not puuid:
                            continue
                        try:
                            players_data.append(self._enrich_player(
                                puuid, player_entry.get("CharacterID"), "friendly",
                                names_map, party_indices, current_season_id,
                                (player_entry.get("PlayerIdentity") or {}).get("AccountLevel")
                            ))
                        except Exception as e:
                            self.requests.logger(f"Error enriching ally player {puuid}: {e}", tag="warning")

                    for player_entry in enemy_players:
                        puuid = player_entry.get("Subject")
                        if not puuid:
                            continue
                        try:
                            players_data.append(self._enrich_player(
                                puuid, player_entry.get("CharacterID"), "enemy",
                                names_map, party_indices, current_season_id,
                                (player_entry.get("PlayerIdentity") or {}).get("AccountLevel")
                            ))
                        except Exception as e:
                            self.requests.logger(f"Error enriching enemy player {puuid}: {e}", tag="warning")

                    return {
                        "MatchID": match_id,
                        "players": players_data,
                    }
                else:
                    self.requests.logger("Failed to get pre-game match details.", tag="error")
                    self._current_pregame_match_id = None
                    return {"MatchID": None, "players": []}
            else:
                self.requests.logger("In Menus or not in pregame match.", tag="info")
                self._current_pregame_match_id = None
                return {"MatchID": None, "players": []}  # Return empty if no pregame match found
        except Exception as e:
            self.requests.logger(f"Error in Pregame.get_pregame_data: {e}", tag="error")
            self._current_pregame_match_id = None
            return {"MatchID": None, "players": []}

    def get_pregame_match_id(self):
        global response
        try:
            response = self.requests.fetch(url_type="glz", endpoint=f"/pregame/v1/players/{self.requests.puuid}", method="get")
            if response.get("errorCode") == "RESOURCE_NOT_FOUND":
                return 0
            match_id = response['MatchID']
            self.requests.logger(f"retrieved pregame match id: '{match_id}'", tag="debug")
            return match_id
        except (KeyError, TypeError):
            self.requests.logger(f"cannot find pregame match id: {response}", tag="debug")
            # print(f"No match id found. {response}")
            try:
                self.response = self.requests.fetch(url_type="glz", endpoint=f"/pregame/v1/players/{self.requests.puuid}", method="get")
                match_id = self.response['MatchID']
                self.requests.logger(f"retrieved pregame match id: '{match_id}'", tag="debug")
                return match_id
            except (KeyError, TypeError):
                self.requests.logger("cannot find pregame match id: ", tag="debug")
                print(f"No match id found. {self.response}")
            return 0

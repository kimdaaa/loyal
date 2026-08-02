import os
import json
import time
import base64

class Presences:
    def __init__(self, Requests):
        self.Requests = Requests

    def get_presence(self):
        pres = self.Requests.fetch(url_type="local", endpoint="/chat/v4/presences", method="get")
        return pres.get('presences', [])

    def get_private_presence(self, presences):
        for presence in presences:
            if presence['puuid'] == self.Requests.puuid and not (presence.get("championId") or presence.get("product") == "league_of_legends"):
                # Add this check:
                if 'private' in presence and presence['private'] is not None:
                    return json.loads(base64.b64decode(presence['private']))
        return None

    def get_game_state(self, presences):
        private = self.get_private_presence(presences)
        if not private:
            return None
        # Riot moved sessionLoopState under matchPresenceData at some point;
        # fall back to the old top-level location in case that ever reverts.
        match_data = private.get("matchPresenceData") or {}
        return match_data.get("sessionLoopState", private.get("sessionLoopState"))

    def wait_for_presence(self, puuids):
        while True:
            if all(puuid in str(self.get_presence()) for puuid in puuids):
                break
            time.sleep(1)
    def decode_presence(self, private):
        if private and "{" not in str(private):
            try:
                return json.loads(base64.b64decode(str(private)).decode("utf-8"))
            except Exception:
                return None
        return None

    def get_party_map(self, presences):
        """Returns {puuid: party_id} for every presence entry with a decodable private
        presence that has a partyId. Skips League of Legends product entries and entries
        with no/undecodable private presence."""
        party_map = {}
        for presence in presences:
            if presence.get("product") == "league_of_legends":
                continue
            decoded = self.decode_presence(presence.get("private"))
            if decoded and decoded.get("partyId"):
                party_map[presence.get("puuid")] = decoded["partyId"]
        return party_map

    def assign_party_indices(self, party_map):
        """Given {puuid: party_id} from get_party_map, returns {puuid: color_index} —
        only for puuids in a party of 2+ members. Solo players are omitted entirely
        (not included in the returned dict). color_index starts at 0 and increments per
        distinct multi-member party, in the order parties are first encountered."""
        from collections import defaultdict
        groups = defaultdict(list)
        for puuid, party_id in party_map.items():
            groups[party_id].append(puuid)
        indices = {}
        idx = 0
        for party_id, members in groups.items():
            if len(members) < 2:
                continue
            for puuid in members:
                indices[puuid] = idx
            idx += 1
        return indices


class Stats:
    def __init__(self):
        self.path = os.path.join(os.getenv('APPDATA'), "rankchecker", "stats.json")
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def save_data(self, data):
        all_data = self.read_data()
        for puuid, entry in data.items():
            entries = all_data.setdefault(puuid, [])
            if isinstance(entry, dict) and entry.get("match_id"):
                if any(isinstance(old, dict) and old.get("match_id") == entry["match_id"] for old in entries):
                    continue
            entries.append(entry)
        with open(self.path, "w") as f:
            json.dump(all_data, f)

    def read_data(self):
        try:
            with open(self.path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    @staticmethod
    def convert_time(seconds):
        s = int(seconds)
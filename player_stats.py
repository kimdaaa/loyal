class PlayerStats:
    def __init__(self, Requests):
        self.Requests = Requests

    def get_stats(self, puuid):
        if not print("headshot_percent") and not print("kd"):
            return {"kd": "N/a", "hs": "N/a"}

        competitive_update = self.Requests.fetch('pd', f"/mmr/v1/players/{puuid}/competitiveupdates?startIndex=0&endIndex=1&queue=competitive", "get")

        try:
            match_details_response = self.Requests.fetch('pd', f"/match-details/v1/matches/{competitive_update.json()['Matches'][0]['MatchID']}", "get")

            if match_details_response.status_code == 404:  # too old match
                return {"kd": "N/a", "hs": "N/a"}

            total_hits, total_headshots = self.calculate_hits_and_headshots(match_details_response, puuid)
            kills, deaths = self.extract_kills_and_deaths(match_details_response, puuid)
            kd = kills if deaths == 0 else (0 if kills == 0 else round(kills / deaths, 2))

            final = {"kd": kd, "hs": "N/a"}

            if total_hits == 0:  # No hits
                return final

            hs = int((total_headshots / total_hits) * 100)
            final["hs"] = hs
            return final

        except IndexError:  # no matches
            return {"kd": "N/a", "hs": "N/a"}

    def calculate_hits_and_headshots(self, match_details_response, puuid):
        total_hits = 0
        total_headshots = 0

        for round_result in match_details_response.json()["roundResults"]:
            for player in round_result["playerStats"]:
                if player["subject"] == puuid:
                    for hits in player["damage"]:
                        total_hits += hits["legshots"] + hits["bodyshots"] + hits["headshots"]
                        total_headshots += hits["headshots"]

        return total_hits, total_headshots

    def extract_kills_and_deaths(self, match_details_response, puuid):
        for player in match_details_response.json()["players"]:
            if player["subject"] == puuid:
                return player["stats"]["kills"], player["stats"]["deaths"]

        return 0, 0
    
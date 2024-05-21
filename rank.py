import concurrent.futures

class Rank:
    def __init__(self, Requests, ranks_before, Content):
        self.Requests = Requests
        self.Content = Content
        self.ranks_before = ranks_before
        self.requestMap = {}


    def get_request(self, puuid, seasonID):
        response = self.Requests.fetch('pd', f"/mmr/v1/players/6cf07500-2f92-5309-b3ae-17990e01f899", "get")
        return response

    def get_rank(self, puuid, seasonID):
        response = self.get_request(puuid, seasonID)
        final = {
            "rank": 0,
            "rr": 0,
            "leaderboard": 0,
            "peakrank": 0,
            "numberofgames": 0,
            "wr": "N/a",
            "statusgood": False,
            "statuscode": None,
            "peakrankact": None,
            "peakrankep": None,
        }

        try:
            if response.ok:
                r = response.json()
                season_info = r["QueueSkills"]["competitive"]["SeasonalInfoBySeasonID"].get(seasonID)

                if season_info:
                    rankTIER = season_info["CompetitiveTier"]
                    final["rank"] = int(rankTIER)
                    final["rr"] = season_info["RankedRating"]

                    if 21 <= int(rankTIER):
                        final["leaderboard"] = 0
                    elif int(rankTIER) not in (0, 1, 2):
                        final["leaderboard"] = 0

                    max_rank_season, max_rank = seasonID, final["rank"]

                    def process_season(season_data):
                        nonlocal max_rank, max_rank_season
                        wins_by_tier = season_data.get("WinsByTier")
                        if wins_by_tier:
                            for winByTier in wins_by_tier:
                                if season_data["SeasonID"] in self.ranks_before and int(winByTier) > 20:
                                    winByTier = int(winByTier) + 3
                                if int(winByTier) > max_rank:
                                    max_rank, max_rank_season = int(winByTier), season_data["SeasonID"]

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        executor.map(process_season, r["QueueSkills"]["competitive"]["SeasonalInfoBySeasonID"].values())

                    final["peakrank"] = max_rank

                wins = season_info.get("NumberOfWinsWithPlacements", 0)
                total_games = season_info.get("NumberOfGames", 0)

                if total_games:
                    final["numberofgames"] = total_games
                    final["wr"] = int(wins / total_games * 100)
        except (TypeError, KeyError, ZeroDivisionError):
            pass
        finally:
            final["statusgood"] = response.ok
            final["statuscode"] = response.status_code
            peak_rank_act_ep = self.Requests.get_act_episode_from_act_id(max_rank_season)
            final["peakrankact"] = peak_rank_act_ep.get("act")
            final["peakrankep"] = peak_rank_act_ep.get("episode")
            return final


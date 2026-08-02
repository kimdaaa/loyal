import concurrent.futures

from constants import RANK_NAMES


def _resolve_rank_name(tier):
    if tier is not None and 0 <= tier < len(RANK_NAMES):
        return RANK_NAMES[tier]
    return "Unranked"


class Rank:
    def __init__(self, Requests, ranks_before, Content):
        self.Requests = Requests
        self.Content = Content
        self.ranks_before = ranks_before
        self.requestMap = {}


    def get_request(self, puuid, seasonID):
        # NOTE: The PUUID in this fetch call is hardcoded to '6cf07500-2f92-5309-b3ae-17990e01f899'.
        # If this is not intentional for all requests, it should be changed to use the 'puuid' argument.
        response = self.Requests.fetch('pd', f"/mmr/v1/players/{puuid}", "get") # CHANGED puuid here
        return response

    def get_rank(self, puuid, seasonID):
        response = self.get_request(puuid, seasonID)
        final = {
            "rank_name": "Unranked",
            "rr": 0,
            "leaderboard": 0,
            "peak_rank_name": "Unranked",
            "peak_rank_act": None,
            "peak_rank_ep": None,
            "numberofgames": 0,
            "wr": None,
            "statusgood": False,
            "statuscode": None,
        }

        # Always defined before any conditional logic so the finally block
        # (and process_season below) can safely reference them even if
        # season_info ends up falsy.
        max_rank_season = seasonID
        max_rank = 0

        try:
            if response is not None and "errorCode" not in response and "httpStatus" not in response:
                r = response
                season_info = r["QueueSkills"]["competitive"]["SeasonalInfoBySeasonID"].get(seasonID)

                if season_info:
                    rankTIER = season_info["CompetitiveTier"]
                    tier = int(rankTIER)
                    final["rank_name"] = _resolve_rank_name(tier)
                    final["rr"] = season_info["RankedRating"]

                    if 21 <= tier:
                        final["leaderboard"] = 0
                    elif tier not in (0, 1, 2):
                        final["leaderboard"] = 0

                    max_rank_season, max_rank = seasonID, tier

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

                    final["peak_rank_name"] = _resolve_rank_name(max_rank)

                    wins = season_info.get("NumberOfWinsWithPlacements", 0)
                    total_games = season_info.get("NumberOfGames", 0)

                    if total_games:
                        final["numberofgames"] = total_games
                        final["wr"] = int(wins / total_games * 100)
        except (TypeError, KeyError, ZeroDivisionError, AttributeError):
            pass
        finally:
            final["statusgood"] = isinstance(response, dict) and "errorCode" not in response and "httpStatus" not in response
            final["statuscode"] = response.get("httpStatus") if isinstance(response, dict) else None
            try:
                if self.Content and max_rank_season:
                    peak_rank_act_ep = self.Content.get_act_episode_from_act_id(max_rank_season) or {}
                    final["peak_rank_act"] = peak_rank_act_ep.get("act")
                    final["peak_rank_ep"] = peak_rank_act_ep.get("episode")
            except Exception:
                pass
            return final
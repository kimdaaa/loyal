def format_player_entry(puuid, name, tag, rank_data, stats_data, level, agent, skin, party_index=None, team="friendly"):
    """
    Assembles the dict shape the GUI consumes for one player row.

    See project spec for full contract. Never raises; always returns a
    fully-populated dict with sensible defaults when inputs are missing.
    """
    rank_data = rank_data or {}
    stats_data = stats_data or {}

    def _map_stat(value):
        if value is None or value == "N/a":
            return "N/A"
        return value

    wr_value = rank_data.get("wr")
    if isinstance(wr_value, int):
        wr = f"{wr_value}%"
    else:
        wr = "N/A"

    return {
        "puuid": puuid,
        "name": name if name else "Unknown",
        "tag": tag if tag else "",
        "rank": rank_data.get("rank_name") or "Unranked",
        "rr": rank_data.get("rr") or 0,
        "leaderboard_pos": rank_data.get("leaderboard") or 0,
        "peak_rank": rank_data.get("peak_rank_name") or "Unranked",
        "peak_rank_act": rank_data.get("peak_rank_act"),
        "peak_rank_ep": rank_data.get("peak_rank_ep"),
        "kd": _map_stat(stats_data.get("kd")),
        "hs": _map_stat(stats_data.get("hs")),
        "wr": wr,
        "level": level if level else "N/A",
        "agent": agent if agent else "N/A",
        "skins_equipped": skin if skin else "N/A",
        "party_index": party_index,
        "team": team,
    }

"""Headless unit tests for gui/derive.py (spec sections 7, 8, 11).

No display, no network, no backend. `python -m pytest tests/test_derive.py -q`
"""

import importlib.util
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from constants import RANK_COLORS_HEX, PARTY_COLORS_HEX  # noqa: E402


def _load_derive():
    """Load gui/derive.py directly by path.

    Deliberately bypasses ``gui/__init__.py`` so this suite proves derive.py
    is importable with no GUI toolkit present at all (spec section 7).
    """
    path = os.path.join(ROOT, "gui", "derive.py")
    spec = importlib.util.spec_from_file_location("loyal_derive", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


derive = _load_derive()

EM_DASH = derive.EM_DASH
build_view_model = derive.build_view_model
is_anomaly = derive.is_anomaly
party_groups = derive.party_groups
peak_delta = derive.peak_delta
recurrence_map = derive.recurrence_map
team_mean_tier = derive.team_mean_tier
tier_index = derive.tier_index
verdict = derive.verdict


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def mk(**over):
    """A realistic player dict as produced by player_format.format_player_entry."""
    base = {
        "puuid": "p-0",
        "name": "Yuki",
        "tag": "NA1",
        "rank": "Diamond 2",
        "rr": 47,
        "leaderboard_pos": 0,
        "peak_rank": "Diamond 3",
        "peak_rank_act": 2,
        "peak_rank_ep": 7,
        "kd": 1.05,
        "hs": 22,
        "wr": "54%",
        "level": 240,
        "agent": "Jett",
        "skins_equipped": "Prime Vandal",
        "party_index": None,
        "team": "friendly",
    }
    base.update(over)
    return base


def na_player(i=0, team="friendly"):
    """Every optional field at its documented worst."""
    return {
        "puuid": "na-%d" % i,
        "name": "Ghost%d" % i,
        "tag": "N/A",
        "rank": "Unranked",
        "rr": 0,
        "peak_rank": "Unranked",
        "peak_rank_act": None,
        "peak_rank_ep": None,
        "kd": "N/A",
        "hs": "N/A",
        "wr": "N/A",
        "level": "N/A",
        "agent": "N/A",
        "skins_equipped": "N/A",
        "party_index": None,
        "team": team,
    }


def full_lobby():
    players = []
    for i in range(5):
        players.append(mk(puuid="f%d" % i, name="Ally%d" % i, team="friendly",
                          party_index=0 if i < 2 else None))
    for i in range(5):
        players.append(mk(puuid="e%d" % i, name="Foe%d" % i, team="enemy",
                          rank="Ascendant 1", peak_rank="Ascendant 2",
                          party_index=None))
    return players


# ---------------------------------------------------------------------------
# tier_index
# ---------------------------------------------------------------------------

def test_tier_index_valid_names():
    assert tier_index("Unranked") == 0
    assert tier_index("Iron 1") == 3
    assert tier_index("Diamond 2") == 19
    assert tier_index("Radiant") == 27


def test_tier_index_case_and_whitespace_insensitive():
    assert tier_index("  DIAMOND   2 ") == 19
    assert tier_index("diamond2") == 19


def test_tier_index_unknown_none_and_empty():
    assert tier_index("Ultra Radiant") == 0
    assert tier_index(None) == 0
    assert tier_index("") == 0
    assert tier_index(12345) == 0
    assert tier_index({"weird": True}) == 0


# ---------------------------------------------------------------------------
# peak_delta
# ---------------------------------------------------------------------------

def test_peak_delta_basic_and_floor():
    assert peak_delta(mk(rank="Gold 1", peak_rank="Platinum 1")) == 3
    # Peak below current can happen with stale data -- floored at 0.
    assert peak_delta(mk(rank="Immortal 1", peak_rank="Gold 1")) == 0
    assert peak_delta({}) == 0
    assert peak_delta(None) == 0


# ---------------------------------------------------------------------------
# is_anomaly
# ---------------------------------------------------------------------------

def test_is_anomaly_peak_delta_alone_is_not_enough():
    p = mk(rank="Silver 1", peak_rank="Diamond 1", kd="N/A", level="N/A")
    assert peak_delta(p) >= 5
    assert is_anomaly(p, [p]) is False


def test_is_anomaly_requires_high_kd_and_win_rate():
    assert is_anomaly(mk(kd=3.01, wr="60.1%"), []) is True
    assert is_anomaly(mk(kd=3.01, wr="60%"), []) is False
    assert is_anomaly(mk(kd=3.0, wr="61%"), []) is False


def test_is_anomaly_high_kd_high_level_is_not_anomaly():
    assert is_anomaly(mk(kd=3.1, wr="61%", level=800), []) is True


def test_is_anomaly_na_kd():
    assert is_anomaly(mk(kd="N/A", level=42), []) is False


def test_is_anomaly_na_level():
    assert is_anomaly(mk(kd=1.9, level="N/A"), []) is False


def test_is_anomaly_normal_player():
    assert is_anomaly(mk(), []) is False


def test_is_anomaly_kd_boundary():
    assert is_anomaly(mk(kd=3.0, wr="61%"), []) is False
    assert is_anomaly(mk(kd=3.01, wr="61%"), []) is True


def test_is_anomaly_never_raises_on_garbage():
    for bad in (None, {}, [], "player", 7, {"kd": object(), "wr": object()}):
        assert is_anomaly(bad, None) in (True, False)


# ---------------------------------------------------------------------------
# team_mean_tier
# ---------------------------------------------------------------------------

def test_team_mean_tier_empty_list():
    assert team_mean_tier([]) == 0.0
    assert team_mean_tier(None) == 0.0


def test_team_mean_tier_all_unranked():
    assert team_mean_tier([mk(rank="Unranked"), mk(rank="Unranked")]) == 0.0


def test_team_mean_tier_mixed_ignores_unranked():
    players = [mk(rank="Gold 1"), mk(rank="Gold 3"), mk(rank="Unranked")]
    # Gold 1 = 12, Gold 3 = 14 -> 13.0, the Unranked entry is ignored.
    assert team_mean_tier(players) == 13.0


def test_team_mean_tier_garbage_entries():
    assert team_mean_tier(["nope", None, 5]) == 0.0


# ---------------------------------------------------------------------------
# verdict
# ---------------------------------------------------------------------------

def test_verdict_even_boundary():
    text, delta = verdict(10.0, 10.49)
    assert text == "EVEN"
    assert abs(delta - 0.49) < 1e-9

    text, _ = verdict(10.0, 10.5)
    assert text == "OUTMATCHED"

    text, _ = verdict(10.0, 9.51)
    assert verdict(10.0, 9.6)[0] == "EVEN"
    assert verdict(10.0, 9.5)[0] == "FAVOURED"


def test_verdict_direction_and_garbage():
    assert verdict(5, 12)[0] == "OUTMATCHED"
    assert verdict(12, 5)[0] == "FAVOURED"
    assert verdict(0, 0) == ("EVEN", 0.0)
    assert verdict(None, "N/A")[0] == "EVEN"


# ---------------------------------------------------------------------------
# party_groups
# ---------------------------------------------------------------------------

def test_party_groups_label():
    players = [
        mk(party_index=0), mk(party_index=0),
        mk(party_index=None), mk(party_index=None), mk(party_index=None),
    ]
    g = party_groups(players)
    assert g["total"] == 5
    assert g["solo"] == 3
    assert g["parties"] == {0: 2}
    assert g["label"] == "5 UNITS · 1 PARTY(2) · 3 SOLO"


def test_party_groups_empty_and_garbage():
    assert party_groups([])["total"] == 0
    assert party_groups(None)["label"] == "0 UNITS"
    assert party_groups(["junk", None])["total"] == 2


def test_party_groups_lone_party_index_counts_as_solo():
    g = party_groups([mk(party_index=3), mk(party_index=None)])
    assert g["parties"] == {}
    assert g["solo"] == 2


# ---------------------------------------------------------------------------
# recurrence_map
# ---------------------------------------------------------------------------

def test_recurrence_map_parses_backend_format():
    lines = [
        "ravenwing#001 (played 2x before)",
        "Yuki#NA1 (played 11x before)",
    ]
    assert recurrence_map(lines) == {"ravenwing#001": 2, "Yuki#NA1": 11}


def test_recurrence_map_skips_garbage_never_raises():
    lines = [
        "ravenwing#001 (played 2x before)",
        "",
        None,
        "totally unparseable line",
        "brokenplayer (played many x before)",
        12345,
        {"not": "a line"},
        "(played 3x before)",
        "trailing#tag (played 0x before)",
    ]
    out = recurrence_map(lines)
    assert out == {"ravenwing#001": 2}


def test_recurrence_map_non_list_input():
    assert recurrence_map(None) == {}
    assert recurrence_map("a string") == {}


# ---------------------------------------------------------------------------
# build_view_model -- shape contract (spec section 8)
# ---------------------------------------------------------------------------

TONES = ("hi", "normal", "dim")


def assert_vm_shape(vm):
    assert set(vm) >= {"state", "state_label", "state_sub", "assessment", "flags", "sides"}
    assert vm["state"] in ("AWAITING", "MENUS", "PREGAME", "INGAME", "OFFLINE")
    a = vm["assessment"]
    assert set(a) == {"show", "friendly", "hostile", "verdict", "delta_label"}
    assert isinstance(a["show"], bool)
    for side in ("friendly", "hostile"):
        assert set(a[side]) == {"label", "pct"}
        assert isinstance(a[side]["pct"], int)
        assert a[side]["label"]
    assert isinstance(vm["flags"], list)
    for f in vm["flags"]:
        assert set(f) == {"kind", "text", "who"}
        assert f["kind"] in ("smurf", "recurrence", "stack")
    assert set(vm["sides"]) == {"friendly", "hostile"}
    for side in ("friendly", "hostile"):
        s = vm["sides"][side]
        assert set(s) >= {"visible", "label", "players"}
        assert isinstance(s["visible"], bool)
        assert isinstance(s["label"], str) and s["label"]
        for p in s["players"]:
            assert_player_shape(p)


def assert_player_shape(p):
    expected = {
        "puuid", "name", "tag", "agent", "sub", "rank", "rank_color", "rank_text",
        "tier_pct", "rr", "peak", "peak_delta", "peak_act", "peak_hi", "stats",
        "party_color", "anomaly", "recurrence",
    }
    assert set(p) == expected, set(p) ^ expected
    assert isinstance(p["stats"], list) and len(p["stats"]) == 4
    for cell in p["stats"]:
        assert set(cell) == {"v", "tone"}
        assert isinstance(cell["v"], str) and cell["v"] != ""
        assert cell["tone"] in TONES
    assert p["rank_color"] in RANK_COLORS_HEX
    assert p["rank_text"] in ("#000000", "#FFFFFF")
    assert p["party_color"] is None or p["party_color"] in PARTY_COLORS_HEX
    assert isinstance(p["tier_pct"], int)
    assert isinstance(p["peak_delta"], int)
    assert isinstance(p["peak_hi"], bool)
    assert isinstance(p["anomaly"], bool)
    assert isinstance(p["recurrence"], int)
    assert isinstance(p["sub"], str) and p["sub"] != ""


def test_build_view_model_empty_player_list():
    vm = build_view_model([], [], None, False)
    assert_vm_shape(vm)
    assert vm["state"] == "AWAITING"
    assert vm["state_label"] == "AWAITING RIOT CLIENT"
    assert vm["assessment"]["show"] is False
    assert vm["sides"]["hostile"]["visible"] is False
    assert vm["sides"]["friendly"]["players"] == []


def test_build_view_model_menus_friendly_only():
    players = [mk(puuid="f%d" % i, team="friendly", party_index=0) for i in range(3)]
    vm = build_view_model(players, [], "MENUS", False)
    assert_vm_shape(vm)
    assert vm["state"] == "MENUS"
    assert vm["state_label"] == "MENUS"
    assert vm["state_sub"] == "IDLE"
    assert vm["sides"]["friendly"]["visible"] is True
    assert len(vm["sides"]["friendly"]["players"]) == 3
    assert vm["sides"]["hostile"]["visible"] is False
    assert vm["assessment"]["show"] is False


def test_build_view_model_menus_hides_hostile_even_if_enemies_present():
    players = full_lobby()
    vm = build_view_model(players, [], "MENUS", False)
    assert vm["sides"]["hostile"]["visible"] is False


def test_build_view_model_full_ten_player_lobby():
    players = full_lobby()
    played_with = ["Foe0#NA1 (played 3x before)"]
    vm = build_view_model(players, played_with, "INGAME", False)
    assert_vm_shape(vm)
    assert vm["state"] == "INGAME"
    assert vm["state_label"] == "MATCH LIVE"
    assert len(vm["sides"]["friendly"]["players"]) == 5
    assert len(vm["sides"]["hostile"]["players"]) == 5
    assert vm["sides"]["hostile"]["visible"] is True
    assert vm["assessment"]["show"] is True
    # Ascendant 1 (21) vs Diamond 2 (19) -> hostile ahead by 2 tiers.
    assert vm["assessment"]["verdict"] == "OUTMATCHED"
    assert vm["assessment"]["delta_label"] == "Δ +2.0 TIERS"
    foe0 = [p for p in vm["sides"]["hostile"]["players"] if p["name"] == "Foe0"][0]
    assert foe0["recurrence"] == 3
    assert any(f["kind"] == "recurrence" for f in vm["flags"])
    assert any(f["kind"] == "stack" for f in vm["flags"])
    ally0 = [p for p in vm["sides"]["friendly"]["players"] if p["name"] == "Ally0"][0]
    assert ally0["party_color"] == PARTY_COLORS_HEX[0]
    assert vm["sides"]["friendly"]["label"] == "5 UNITS · 1 PARTY(2) · 3 SOLO"


def test_build_view_model_all_stats_na():
    players = [na_player(i, "friendly") for i in range(5)]
    players += [na_player(i + 5, "enemy") for i in range(5)]
    vm = build_view_model(players, None, "PREGAME", False)
    assert_vm_shape(vm)
    assert vm["state_label"] == "AGENT SELECT"
    for side in ("friendly", "hostile"):
        for p in vm["sides"][side]["players"]:
            assert [c["v"] for c in p["stats"]] == [EM_DASH] * 4
            assert [c["tone"] for c in p["stats"]] == ["dim"] * 4
            assert p["rank_color"] == "#2E2E2E"
            assert p["peak_act"] == EM_DASH
            assert p["sub"] != ""
            assert p["agent"] == ""
    assert vm["assessment"]["verdict"] == "EVEN"


def test_build_view_model_stale_wins_over_game_state():
    vm = build_view_model(full_lobby(), [], "INGAME", True)
    assert vm["state"] == "OFFLINE"
    assert vm["state_label"] == "VALORANT OFFLINE"
    assert vm["state_sub"] == "STALE 30s"
    # Roster retained while stale (spec section 11).
    assert len(vm["sides"]["hostile"]["players"]) == 5
    assert vm["sides"]["hostile"]["visible"] is True


def test_build_view_model_hostile_hidden_when_no_enemies():
    vm = build_view_model([mk()], [], "INGAME", False)
    assert vm["sides"]["hostile"]["visible"] is False
    assert vm["assessment"]["show"] is False


def test_stat_tones():
    p = mk(kd=1.55, hs=31, wr="61%", level=300)
    vm = build_view_model([p, mk(team="enemy")], [], "INGAME", False)
    stats = vm["sides"]["friendly"]["players"][0]["stats"]
    assert stats[0] == {"v": "1.55", "tone": "hi"}
    assert stats[1] == {"v": "31%", "tone": "hi"}
    assert stats[2] == {"v": "61%", "tone": "hi"}
    assert stats[3] == {"v": "300", "tone": "normal"}


def test_tier_pct_and_rank_text_luminance():
    vm = build_view_model([mk(rank="Radiant")], [], "INGAME", False)
    p = vm["sides"]["friendly"]["players"][0]
    assert p["tier_pct"] == 100
    assert p["rank_color"] == "#FFFDCD"
    assert p["rank_text"] == "#000000"          # pale pill -> black text
    vm2 = build_view_model([mk(rank="Iron 1")], [], "INGAME", False)
    assert vm2["sides"]["friendly"]["players"][0]["rank_text"] == "#FFFFFF"


def test_contrast_text_color_matches_theme_heuristic():
    assert derive.contrast_text_color("#FFFFFF") == "#000000"
    assert derive.contrast_text_color("#000000") == "#FFFFFF"
    assert derive.contrast_text_color("not a colour") == "#FFFFFF"
    assert derive.contrast_text_color(None) == "#FFFFFF"


# ---------------------------------------------------------------------------
# pathological input -- nothing may raise
# ---------------------------------------------------------------------------

PATHOLOGICAL_PLAYERS = [
    None,
    {},
    {"name": None, "tag": None, "rank": None, "peak_rank": None, "kd": None,
     "hs": None, "wr": None, "level": None, "party_index": "seven",
     "agent": None, "skins_equipped": None, "team": None},
    {"rank": 42, "peak_rank": [], "kd": {}, "hs": object(), "wr": float("nan"),
     "level": float("inf"), "party_index": -3, "team": "enemy", "rr": "N/A"},
    {"name": "x" * 500, "tag": "#" * 50, "rank": "Ultra Radiant Prime",
     "peak_rank": "Radiant", "kd": "1,25", "hs": "33%", "wr": "not a number",
     "level": True, "party_index": 9999, "team": "ENEMY"},
    "not a dict at all",
    12345,
    ["a", "list"],
]


@pytest.mark.parametrize("game_state", [None, "", "MENUS", "PREGAME", "INGAME", "BOGUS", 7, []])
@pytest.mark.parametrize("stale", [True, False, None, "yes"])
def test_build_view_model_never_raises(game_state, stale):
    vm = build_view_model(PATHOLOGICAL_PLAYERS, ["garbage", None, 5], game_state, stale)
    assert_vm_shape(vm)


def test_build_view_model_never_raises_on_non_list_players():
    for bad in (None, "players", 7, {"a": 1}, object()):
        vm = build_view_model(bad, None, None, None)
        assert_vm_shape(vm)


def test_pure_functions_never_raise_on_pathological_input():
    for bad in PATHOLOGICAL_PLAYERS:
        assert isinstance(tier_index(bad), int)
        assert isinstance(peak_delta(bad), int)
        assert isinstance(is_anomaly(bad, PATHOLOGICAL_PLAYERS), bool)
    assert isinstance(team_mean_tier(PATHOLOGICAL_PLAYERS), float)
    assert isinstance(party_groups(PATHOLOGICAL_PLAYERS), dict)
    assert isinstance(recurrence_map(PATHOLOGICAL_PLAYERS), dict)
    assert isinstance(verdict(object(), object()), tuple)


def test_module_is_headless_and_pure():
    """No GUI / IO imports leak in via gui.derive."""
    src = open(derive.__file__, "r", encoding="utf-8").read()
    for forbidden in ("import webview", "import tkinter", "customtkinter",
                      "import requests", "open(", "import socket"):
        assert forbidden not in src

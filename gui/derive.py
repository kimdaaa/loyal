"""
Pure derivation layer for the MAGI UI (spec section 7 / 8).

Everything in this module is a pure function of its arguments. There is no
pywebview import, no Tk, no network, no file I/O and no global mutable state,
so the whole module is importable and fully exercisable headless.

The only project dependency is ``constants`` (rank names, rank colours, party
colours) -- the single source of truth for colour, per spec section 9.

ROBUSTNESS CONTRACT
-------------------
Real player dicts routinely contain the string ``"N/A"`` where a number is
documented, ``None`` for ``peak_rank_act`` / ``peak_rank_ep``, and rank names
that are not in ``constants.RANK_NAMES``. **No function in this module may
raise for any input.** Every value that crosses the boundary goes through one
of the coercion helpers below.
"""

from __future__ import annotations

import re

from constants import RANK_NAMES, RANK_COLORS_HEX, PARTY_COLORS_HEX

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EM_DASH = "—"          # the "no value" glyph -- never emit a blank stat
MAX_TIER = 27               # index of Radiant in RANK_NAMES
UNRANKED_COLOR = "#2E2E2E"

TONE_HI = "hi"
TONE_NORMAL = "normal"
TONE_DIM = "dim"

# Peak marker is separate from the live anomaly decision.
SMURF_PEAK_DELTA = 5
SMURF_KD = 3.0
SMURF_WR = 60.0

# Stat "interesting" thresholds, used only to pick a tone.
HI_KD = 1.4
HI_HS = 25.0
HI_WR = 55.0

# Placard copy -- spec section 5.
_STATE_TEXT = {
    "AWAITING": ("AWAITING RIOT CLIENT", "NO BACKEND"),
    "MENUS": ("MENUS", "IDLE"),
    "PREGAME": ("AGENT SELECT", "PREGAME"),
    "INGAME": ("MATCH LIVE", "INGAME"),
    "OFFLINE": ("VALORANT OFFLINE", "STALE 30s"),
}

# Rank name -> short placard token ("Diamond 2" -> "D2").
_RANK_INITIALS = {
    "iron": "I",
    "bronze": "B",
    "silver": "S",
    "gold": "G",
    "platinum": "P",
    "diamond": "D",
    "ascendant": "A",
    "immortal": "IM",
    "radiant": "RAD",
    "unranked": "UNR",
}

# "name#tag (played 3x before)" -- see app_backend._update_played_with.
_PLAYED_WITH_RE = re.compile(
    r"^\s*(?P<who>\S.*?)\s*\(\s*played\s+(?P<count>\d+)\s*x\b", re.IGNORECASE
)

# Index lookup built once; lower-cased and whitespace-normalised so that
# "diamond  2" and "DIAMOND 2" both resolve.
_RANK_INDEX = {}
for _i, _name in enumerate(RANK_NAMES):
    _key = " ".join(str(_name).lower().split())
    # First occurrence wins: the three "Unranked" entries collapse to 0.
    _RANK_INDEX.setdefault(_key, _i)


# ---------------------------------------------------------------------------
# Defensive coercion helpers
# ---------------------------------------------------------------------------

def _as_dict(value):
    """Return ``value`` if it is a dict, else an empty dict."""
    return value if isinstance(value, dict) else {}


def _as_list(value):
    """Return a list for anything list-like; ``[]`` for None/garbage."""
    if isinstance(value, (list, tuple)):
        return list(value)
    return []


def _as_text(value):
    """Coerce to a stripped string. ``None`` and non-strings become ``""``."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    try:
        return str(value).strip()
    except Exception:
        return ""


def _is_missing(value):
    """True for the many shapes 'no data' takes in this codebase."""
    if value is None:
        return True
    if isinstance(value, str):
        return _as_text(value).upper() in ("", "N/A", "NA", "NONE", "NULL", "-", EM_DASH)
    return False


def _as_number(value):
    """Coerce to float, or ``None`` when the value is missing/unparseable.

    Tolerates ``"1.34"``, ``"53%"``, ``"N/A"``, ``None``, bools and objects.
    """
    if _is_missing(value):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            f = float(value)
        except Exception:
            return None
        if f != f or f in (float("inf"), float("-inf")):  # NaN / inf
            return None
        return f
    text = _as_text(value)
    if not text:
        return None
    cleaned = text.replace("%", "").replace(",", "").strip()
    try:
        f = float(cleaned)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float("inf"), float("-inf")):
        return None
    return f


def _as_whole(value):
    """Coerce to int, or ``None``. ``"142"`` -> 142, ``"N/A"`` -> None."""
    n = _as_number(value)
    if n is None:
        return None
    try:
        return int(n)
    except Exception:
        return None


def _get(player, key, default=None):
    """dict.get that survives ``player`` not being a dict at all."""
    return _as_dict(player).get(key, default)


def _hex_to_rgb(hex_color):
    h = _as_text(hex_color).lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError("bad hex colour")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def contrast_text_color(hex_color):
    """Port of ``gui.theme.contrast_text_color``.

    ITU-R BT.601 perceived luminance, threshold 0.6: light pills get black
    text, dark pills get white. Never raises.
    """
    try:
        r, g, b = _hex_to_rgb(hex_color)
    except Exception:
        return "#FFFFFF"
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#000000" if luminance > 0.6 else "#FFFFFF"


# ---------------------------------------------------------------------------
# Section 7 -- derived intelligence
# ---------------------------------------------------------------------------

def tier_index(rank_name):
    """Index of ``rank_name`` into ``constants.RANK_NAMES`` (0-27).

    Unknown names, ``None``, ``""`` and non-strings all fall back to 0
    (Unranked). Case- and whitespace-insensitive.
    """
    key = " ".join(_as_text(rank_name).lower().split())
    if not key:
        return 0
    idx = _RANK_INDEX.get(key)
    if idx is not None:
        return idx
    # Tolerate "Diamond2" / "diamond-2" style variants.
    compact = re.sub(r"[^a-z0-9]", "", key)
    for name, i in _RANK_INDEX.items():
        if re.sub(r"[^a-z0-9]", "", name) == compact:
            return i
    return 0


def peak_delta(player):
    """``tier_index(peak_rank) - tier_index(rank)``, floored at 0."""
    p = _as_dict(player)
    delta = tier_index(p.get("peak_rank")) - tier_index(p.get("rank"))
    return delta if delta > 0 else 0


def is_anomaly(player, lobby=None):
    """Flag only a high-confidence smurf signal from KDA and win rate."""
    p = _as_dict(player)
    try:
        kd = _as_number(p.get("kd"))
        wr = _as_number(p.get("wr"))
        return kd is not None and wr is not None and kd > SMURF_KD and wr > SMURF_WR
    except Exception:
        return False
    return False

def team_mean_tier(players):
    """Mean tier index for a side.

    Ignores unranked players (index 0) so one unresolved account does not drag
    the whole team's reading down -- unless *every* player is unranked, in
    which case the mean is 0.0. Empty/garbage input -> 0.0.
    """
    tiers = [tier_index(_get(p, "rank")) for p in _as_list(players)]
    if not tiers:
        return 0.0
    ranked = [t for t in tiers if t > 0]
    pool = ranked if ranked else tiers
    if not pool:
        return 0.0
    return float(sum(pool)) / float(len(pool))


def verdict(friendly_mean, hostile_mean):
    """``(verdict_text, delta)`` where delta is ``hostile - friendly``.

    ``EVEN`` when ``abs(delta) < 0.5``; otherwise ``OUTMATCHED`` when the
    hostile side is higher, ``FAVOURED`` when the friendly side is.
    """
    f = _as_number(friendly_mean) or 0.0
    h = _as_number(hostile_mean) or 0.0
    delta = h - f
    if abs(delta) < 0.5:
        return "EVEN", delta
    if delta > 0:
        return "OUTMATCHED", delta
    return "FAVOURED", delta


def party_groups(players):
    """Party composition for one side.

    ``party_index is None`` means solo. Returns::

        {
          "total": 5,
          "solo": 3,
          "parties": {0: 2},              # party_index -> member count
          "label": "5 UNITS · 1 PARTY(2) · 3 SOLO",
        }

    Parties of one are counted as solo -- a "party" of one is not a stack.
    """
    roster = _as_list(players)
    counts = {}
    solo = 0
    for p in roster:
        idx = _get(p, "party_index")
        if idx is None or isinstance(idx, bool):
            solo += 1
            continue
        key = _as_whole(idx)
        if key is None:
            solo += 1
            continue
        counts[key] = counts.get(key, 0) + 1

    real_parties = {k: v for k, v in counts.items() if v >= 2}
    solo += sum(v for k, v in counts.items() if v < 2)

    total = len(roster)
    parts = ["%d UNITS" % total]
    if real_parties:
        sizes = sorted(real_parties.values(), reverse=True)
        parts.append(
            "%d PARTY(%s)" % (len(sizes), ",".join(str(s) for s in sizes))
        )
    if solo:
        parts.append("%d SOLO" % solo)

    return {
        "total": total,
        "solo": solo,
        "parties": real_parties,
        "label": " · ".join(parts),
    }


def recurrence_map(played_with_lines):
    """Parse ``get_played_with_players_for_ui()`` lines into counts.

    Expected shape: ``"name#tag (played 3x before)"``. Unparseable lines are
    skipped silently; this function never raises. Duplicate keys keep the
    highest count seen.
    """
    out = {}
    for line in _as_list(played_with_lines):
        try:
            text = _as_text(line)
            if not text:
                continue
            m = _PLAYED_WITH_RE.match(text)
            if not m:
                continue
            who = m.group("who").strip()
            if not who:
                continue
            count = _as_whole(m.group("count"))
            if count is None or count <= 0:
                continue
            if count > out.get(who, 0):
                out[who] = count
        except Exception:
            continue
    return out


# ---------------------------------------------------------------------------
# Section 8 -- view model assembly
# ---------------------------------------------------------------------------

def _stat(value, tone_fn=None, fmt=None, suffix=""):
    """Build one ``{"v":…, "tone":…}`` stat cell.

    Missing values always render as a dimmed em dash -- never a blank string.
    """
    n = _as_number(value)
    if n is None:
        return {"v": EM_DASH, "tone": TONE_DIM}
    try:
        text = fmt(n) if fmt else _as_text(value)
    except Exception:
        text = _as_text(value)
    if not text:
        text = EM_DASH
        return {"v": text, "tone": TONE_DIM}
    text = "%s%s" % (text, suffix)
    tone = TONE_NORMAL
    if tone_fn is not None:
        try:
            tone = tone_fn(n) or TONE_NORMAL
        except Exception:
            tone = TONE_NORMAL
    return {"v": text, "tone": tone}


def _player_stats(player):
    """The four stat cells, always in order K/D, HS, WR, LVL."""
    p = _as_dict(player)
    return [
        _stat(
            p.get("kd"),
            tone_fn=lambda n: TONE_HI if n >= HI_KD else TONE_NORMAL,
            fmt=lambda n: "%.2f" % n,
        ),
        _stat(
            p.get("hs"),
            tone_fn=lambda n: TONE_HI if n >= HI_HS else TONE_NORMAL,
            fmt=lambda n: "%d" % round(n),
            suffix="%",
        ),
        _stat(
            p.get("wr"),
            tone_fn=lambda n: TONE_HI if n >= HI_WR else TONE_NORMAL,
            fmt=lambda n: "%d" % round(n),
            suffix="%",
        ),
        _stat(
            p.get("level"),
            tone_fn=lambda n: TONE_NORMAL,
            fmt=lambda n: "%d" % round(n),
        ),
    ]


def _rank_colors(rank_name):
    """``(fill, text)`` for the rank pill, straight from constants."""
    idx = tier_index(rank_name)
    try:
        fill = RANK_COLORS_HEX[idx]
    except Exception:
        fill = UNRANKED_COLOR
    if not _as_text(fill):
        fill = UNRANKED_COLOR
    return fill, contrast_text_color(fill)


def party_color(party_index):
    """Party spine colour, or ``None`` for solo. Wraps the palette."""
    if party_index is None or isinstance(party_index, bool):
        return None
    idx = _as_whole(party_index)
    if idx is None:
        return None
    if not PARTY_COLORS_HEX:
        return None
    return PARTY_COLORS_HEX[idx % len(PARTY_COLORS_HEX)]


def _peak_act_label(player):
    """``"E7 · A2"`` -- em dash when neither episode nor act is known."""
    p = _as_dict(player)
    ep = _as_whole(p.get("peak_rank_ep"))
    act = _as_whole(p.get("peak_rank_act"))
    if ep is None and act is None:
        return EM_DASH
    left = "E%d" % ep if ep is not None else "E?"
    right = "A%d" % act if act is not None else "A?"
    return "%s · %s" % (left, right)


def _sub_label(agent, skin):
    """``"JETT · Prime Vandal"``; degrades to whichever half is known."""
    a = "" if _is_missing(agent) else _as_text(agent).upper()
    if a.startswith("N/A"):
        a = ""
    s = "" if _is_missing(skin) else _as_text(skin)
    parts = [x for x in (a, s) if x]
    if not parts:
        return EM_DASH
    return " · ".join(parts)


def _clean_agent(agent):
    """Agent name for the portrait lookup; ``""`` in menus / when unknown."""
    if _is_missing(agent):
        return ""
    text = _as_text(agent)
    if text.upper().startswith("N/A"):
        return ""
    return text


def _display_key(player):
    """``"name#tag"`` as printed by the backend's played-with lines."""
    p = _as_dict(player)
    name = _as_text(p.get("name"))
    tag = _as_text(p.get("tag"))
    if tag:
        return "%s#%s" % (name, tag)
    return name


def rank_abbrev(tier):
    """``19 -> "D2"``. Used by the balance meter labels."""
    idx = _as_whole(tier)
    if idx is None:
        idx = 0
    idx = max(0, min(MAX_TIER, idx))
    try:
        name = str(RANK_NAMES[idx])
    except Exception:
        return "UNR"
    parts = name.split()
    initial = _RANK_INITIALS.get(parts[0].lower())
    if initial is None:
        initial = parts[0][:1].upper() or "UNR"
    if len(parts) > 1 and parts[1].isdigit():
        return "%s%s" % (initial, parts[1])
    return initial


def _meter(mean_tier):
    """One side of the balance meter: ``{"label": "D2 · 40", "pct": 64}``."""
    mean = _as_number(mean_tier) or 0.0
    mean = max(0.0, min(float(MAX_TIER), mean))
    whole = int(mean)
    frac = int(round((mean - whole) * 100))
    if frac >= 100:
        frac = 99
    pct = int(round(mean / MAX_TIER * 100))
    return {
        "label": "%s · %02d" % (rank_abbrev(whole), frac),
        "pct": pct,
    }


def resolve_state(game_state, stale):
    """``(state, label, sub)`` for the status placard (spec section 5)."""
    if stale:
        state = "OFFLINE"
    else:
        gs = _as_text(game_state).upper()
        state = gs if gs in ("MENUS", "PREGAME", "INGAME") else "AWAITING"
    label, sub = _STATE_TEXT.get(state, _STATE_TEXT["AWAITING"])
    return state, label, sub


def _build_player(player, recurrence):
    p = _as_dict(player)
    rank_name = _as_text(p.get("rank")) or "Unranked"
    tier = tier_index(rank_name)
    fill, text_color = _rank_colors(rank_name)
    delta = peak_delta(p)
    peak_name = _as_text(p.get("peak_rank")) or "Unranked"
    agent = _clean_agent(p.get("agent"))
    key = _display_key(p)

    return {
        "puuid": _as_text(p.get("puuid")),
        "name": _as_text(p.get("name")) or "Unknown",
        "tag": _as_text(p.get("tag")),
        "agent": agent,
        "sub": _sub_label(p.get("agent"), p.get("skins_equipped")),
        "rank": rank_name.upper(),
        "rank_color": fill,
        "rank_text": text_color,
        "tier_pct": int(round(tier / MAX_TIER * 100)),
        "rr": _as_whole(p.get("rr")) or 0,
        "peak": peak_name,
        "peak_delta": delta,
        "peak_act": _peak_act_label(p),
        "peak_hi": delta >= SMURF_PEAK_DELTA,
        "stats": _player_stats(p),
        "party_color": party_color(p.get("party_index")),
        "anomaly": bool(is_anomaly(p)),
        "recurrence": int(_as_dict(recurrence).get(key, 0) or 0),
    }


def _side_label_hostile(entries, slots=5):
    resolved = sum(1 for e in entries if _as_text(e.get("rank")).upper() != "UNRANKED")
    flagged = sum(1 for e in entries if e.get("anomaly"))
    total = max(slots, len(entries))
    label = "%d / %d RESOLVED" % (resolved, total)
    if flagged:
        label += " · %d FLAGGED" % flagged
    return label


def _flags(friendly, hostile, groups_f, groups_h):
    out = []
    for entry in list(friendly) + list(hostile):
        who = entry.get("name", "")
        if entry.get("tag"):
            who = "%s#%s" % (who, entry["tag"])
        if entry.get("anomaly"):
            out.append({
                "kind": "smurf",
                "text": "%s — SMURF PATTERN" % who.upper(),
                "who": who,
            })
        rec = entry.get("recurrence") or 0
        if rec:
            out.append({
                "kind": "recurrence",
                "text": "%s — SEEN %d× BEFORE" % (who.upper(), rec),
                "who": who,
            })
    for side_name, groups in (("FRIENDLY", groups_f), ("HOSTILE", groups_h)):
        for size in sorted(_as_dict(groups).get("parties", {}).values(), reverse=True):
            out.append({
                "kind": "stack",
                "text": "%s STACK OF %d" % (side_name, size),
                "who": "",
            })
    return out


def build_view_model(players, played_with, game_state, stale):
    """Assemble the full Python -> JS view model (spec section 8).

    Never raises. Every field is always present; missing values are rendered
    as a dimmed em dash rather than a blank cell.
    """
    try:
        roster = [p for p in _as_list(players) if isinstance(p, dict)]
        recurrence = recurrence_map(played_with)
        state, state_label, state_sub = resolve_state(game_state, stale)

        friendly_src = [p for p in roster if _as_text(p.get("team")).lower() != "enemy"]
        hostile_src = [p for p in roster if _as_text(p.get("team")).lower() == "enemy"]

        friendly = [_build_player(p, recurrence) for p in friendly_src]
        hostile = [_build_player(p, recurrence) for p in hostile_src]

        groups_f = party_groups(friendly_src)
        groups_h = party_groups(hostile_src)

        f_mean = team_mean_tier(friendly_src)
        h_mean = team_mean_tier(hostile_src)
        verdict_text, delta = verdict(f_mean, h_mean)

        has_hostile = bool(hostile)
        hostile_visible = has_hostile and state != "MENUS"
        balanced_roster = bool(friendly) and bool(hostile) and len(friendly) == len(hostile)

        return {
            "state": state,
            "state_label": state_label,
            "state_sub": state_sub,
            "stale": bool(stale),
            "assessment": {
                "show": balanced_roster,
                "friendly": _meter(f_mean),
                "hostile": _meter(h_mean),
                "verdict": verdict_text,
                "delta_label": "Δ %+.1f TIERS" % delta,
            },
            "flags": _flags(friendly, hostile, groups_f, groups_h),
            "sides": {
                "friendly": {
                    "visible": True,
                    "label": groups_f["label"],
                    "players": friendly,
                },
                "hostile": {
                    "visible": hostile_visible,
                    "label": _side_label_hostile(hostile),
                    "players": hostile,
                },
            },
        }
    except Exception:
        # Absolute last resort: an empty but structurally valid view model.
        return _empty_view_model()


def _empty_view_model():
    label, sub = _STATE_TEXT["AWAITING"]
    zero = _meter(0.0)
    return {
        "state": "AWAITING",
        "state_label": label,
        "state_sub": sub,
        "stale": False,
        "assessment": {
            "show": False,
            "friendly": zero,
            "hostile": dict(zero),
            "verdict": "EVEN",
            "delta_label": "Δ +0.0 TIERS",
        },
        "flags": [],
        "sides": {
            "friendly": {"visible": True, "label": "0 UNITS", "players": []},
            "hostile": {"visible": False, "label": "0 / 5 RESOLVED", "players": []},
        },
    }

# Loyal — MAGI UI Redesign

**Date:** 2026-07-28
**Status:** Approved for implementation
**Supersedes:** the CustomTkinter "Tactical Intel Readout" GUI (`gui/app.py`, `gui/theme.py`, `gui/widgets.py`)

---

## 1. Design direction

An Evangelion/NERV console. Amber-on-black, dense telemetry, hard edges, heavy tracked
condensed type, scanlines. It should feel like a cheat that gets you more information than
you should have — while being nothing but a nicer view of data the app already fetches.

**The governing discipline:** all of the Eva language lives in the *chrome* — rails, corner
marks, letter-spacing, the assessment band, `PATTERN ORANGE` placards, the cruciform burst.
Inside a data row it is flat, aligned, and quiet. Decoration never enters the scan path.
The brief's own priority stands: legibility and scan speed beat decoration.

### Why this beats the current HUD look

The current UI fights CustomTkinter. `theme.tracked()` fakes letter-spacing by joining
characters with spaces; nothing aligns between rows because each card lays itself out
independently; there is no motion. Moving to a webview buys real tracking, tabular numerals,
CSS grid alignment, and 60fps transitions for free.

### Scan intents this screen serves (in priority order)

1. **Who's the threat?** — outliers amplified, everyone else recedes.
2. **How does the lobby stack up?** — aggregate balance before any row is read.
3. **Who's queued together?** — party grouping is structural.
4. **Is anyone a repeat?** — recurrence surfaces inline on the row.

---

## 2. Stack

**pywebview + vanilla HTML/CSS/JS.** No npm, no build step, no bundler.

| Concern | Verdict |
|---|---|
| Look/motion | The whole reason. Tk cannot do tracking, easing, or aligned dense tables. |
| New deps | `pywebview` only. WebView2 runtime ships with Win10/11. No bundled Chromium. |
| Fonts | Bahnschrift, Consolas, Cascadia Mono all ship with Windows. **Nothing to bundle.** |
| Threading | `window.evaluate_js()` is callable from any thread — simpler than Tk's `after(0,…)` hop. |
| Packaging | PyInstaller still works; `gui/web/` ships as data files. |
| Risk | Two languages in one repo; debugging goes through devtools. Accepted. |

Rejected: staying on CustomTkinter (ceiling too low for a dense scoreboard), PySide6/Qt
(~150MB dep and LGPL packaging friction for no visual gain over a webview here).

Not a fit for a true always-on-top in-game overlay — explicitly out of scope, this is a
second-monitor window.

---

## 3. Window and layout

- **1600 × 640**, resizable. Two columns: FRIENDLY left, HOSTILE right, 1px spine.
- **Below 1500px wide** one media query collapses to stacked full-width bands. Same CSS,
  no second layout to maintain.
- Bands top to bottom: rail (36) → threat assessment → team columns (flex) → footer.

### Spacing system

Every padding, gap and margin is a token on a **4px scale**: `--s1:4 --s2:8 --s3:12 --s4:16
--s5:20 --s6:24`. A single `--gut:16px` gutter is shared by the rail, assessment, balance
meter, flag rail, side header, column header, rows and footer, giving one continuous left
edge down the window. **No hand-picked values anywhere.**

### Baseline grid (the critical rule)

Every row cell renders **two fixed line boxes**: `--l1:20px` primary, `--l2:14px` secondary.

| Cell | Line 1 | Line 2 |
|---|---|---|
| Operator | `name#tag` + marks | `AGENT · Skin` |
| Rank | rank pill (110px fixed) | tier meter + RR (32px sub-slot) |
| Peak | peak rank + `▲n` | `E{ep} · A{act}` |
| Stats | K/D · HS · WR · LVL | *(empty, reserved)* |

Cells must **not** centre themselves in the row. A one-line cell centring in a two-line row
lands in the dead space between the name and the sub-line — this was the defect that read as
"chopped" during review. Line 1 forms one horizontal across the row, line 2 forms another.

### Row grid

```
44px  |  215px    |  110px  |  90px  |  1fr    |  180px
id    |  operator |  rank   |  peak  | spacer  |  stats(4 × 1fr, 8px gap)
```
16px column gap. Identity cell = 3px party spine + 33px portrait. The `1fr` spacer sits
between PEAK and the stat block so numbers stay welded to the right edge with a clean gutter
separating identity from performance. Stats are **one grid cell** with internal rhythm so the
16px column gap never leaks between the four numbers.

### No dead space, ever

Each side always renders **5 slots**, each `flex: 1 1 0` with a `min-height: 60px`. Unfilled
slots are dashed ghost bays labelled `SLOT 0n · UNRESOLVED`. This removes the gap at any
window height *and* doubles as the honest "still resolving this player" state.

---

## 4. Design tokens

```
--void #07080A   --panel #0C0E11   --panel2 #11141A   --hair #1C222A   --hair2 #141920
--amber #FF6B00  --amber-dim #8A3D00   --amber-glow rgba(255,107,0,.13)
--phos #4AE39B (friendly)   --alert #FF2D3F (hostile)   --blue #6FA8DC (recurrence)
--ink #E8E5DD    --ink2 #8B95A1    --ink3 #525C67
--f-cond 'Bahnschrift','Archivo Narrow','Oswald','Segoe UI',sans-serif
--f-mono 'Cascadia Mono','Consolas',monospace
```

All numerals use `font-variant-numeric: tabular-nums`.

Rank and party colours come from `constants.RANK_COLORS_HEX` / `PARTY_COLORS_HEX`
**verbatim** — no new rank-colour mapping. Pill text colour is chosen by the existing
luminance heuristic (port `theme.contrast_text_color`).

### Marks

- **`⚠ SMURF`** — amber outline tag on the row, plus amber row wash, pulsing 2px left edge,
  and the name goes amber.
- **Cruciform light-burst** — recurrence mark. Tapered concave arms, vertical dominant,
  crossbar high, 9×11px, `--blue`, slow breathing glow so it reads as light not an icon.
  Rendered inline SVG at body-text size after the tag, with a `×n` count.
- **Party spine** — 3px colour bar in the identity cell. Solo = transparent.

---

## 5. Status placard (rail, right)

Driven by real game state. Label, colour and dot behaviour change together so it is readable
peripherally.

| State | Label / sub | Colour | Dot |
|---|---|---|---|
| no backend | `AWAITING RIOT CLIENT` / `NO BACKEND` | amber | slow breathe |
| `MENUS` | `MENUS` / `IDLE` | grey | static |
| `PREGAME` | `AGENT SELECT` / `PREGAME` | amber | fast blink + box pulse |
| `INGAME` | `MATCH LIVE` / `INGAME` | phosphor | slow blink + glow |
| stale >30s | `VALORANT OFFLINE` / `STALE 30s` | red | static |

---

## 6. Threat assessment band

- **Balance meter** — opposing bars from centre. Friendly mean tier (phosphor, grows right→left)
  vs hostile mean tier (red, grows left→right), each with a `D2 · 40` style label.
  Centre shows verdict (`OUTMATCHED` / `EVEN` / `FAVOURED`) and `Δ ±n.n TIERS`.
- **Flag rail** — single non-wrapping horizontal scroll strip, thin amber scrollbar, right
  fade mask and a `n ▸` count. Must never wrap or push the roster down regardless of flag count.

---

## 7. Derived intelligence (presentation layer only)

All of this is computed in the UI layer from the existing player dict. **No backend logic
changes.** Lives in `gui/derive.py` as pure functions — no webview, no I/O, unit-testable
headless.

- `tier_index(rank_name) -> int` — index into `constants.RANK_NAMES` (0–27). Unknown → 0.
- `peak_delta(player) -> int` — `tier_index(peak_rank) - tier_index(rank)`, floored at 0.
- `is_anomaly(player, lobby) -> bool` — smurf heuristic. True when **either**:
  - `peak_delta >= 5` (more than ~1.5 divisions above current), **or**
  - `kd >= 1.4` **and** `level` is numeric and `< 100`.
  Guard every branch: `kd`/`hs`/`level` may be the string `"N/A"`.
- `team_mean_tier(players) -> float` — mean tier index; ignores unranked (index 0) unless all
  are unranked.
- `verdict(friendly_mean, hostile_mean) -> (str, float)` — `EVEN` when `|Δ| < 0.5`.
- `party_groups(players) -> dict` — counts and labels (`5 UNITS · 1 PARTY(2) · 3 SOLO`).
  `party_index is None` means solo.
- `recurrence_map(played_with_lines) -> dict[str, int]` — parse
  `get_played_with_players_for_ui()` lines into `{"name#tag": count}`. Tolerate unparseable
  lines by skipping them; never raise.
- `build_view_model(players, played_with, game_state, stale) -> dict` — assembles §8.

---

## 8. View model (Python → JS contract)

```jsonc
{
  "state": "AWAITING|MENUS|PREGAME|INGAME|OFFLINE",
  "state_label": "AGENT SELECT", "state_sub": "PREGAME",
  "assessment": {
    "show": true,
    "friendly": { "label": "D2 · 40", "pct": 64 },
    "hostile":  { "label": "D3 · 40", "pct": 79 },
    "verdict": "OUTMATCHED", "delta_label": "Δ +1.4 TIERS"
  },
  "flags": [ { "kind": "smurf|recurrence|stack", "text": "…", "who": "ravenwing#001" } ],
  "sides": {
    "friendly": { "visible": true, "label": "5 UNITS · 1 PARTY(2) · 3 SOLO", "players": [ … ] },
    "hostile":  { "visible": true, "label": "4 / 5 RESOLVED · 2 FLAGGED",   "players": [ … ] }
  }
}
```

Player entry:

```jsonc
{
  "puuid": "…",                       // stable diff key
  "name": "Yuki", "tag": "NA1",
  "agent": "Jett",                    // "" when in menus
  "sub": "JETT · Prime Vandal",
  "rank": "DIAMOND 2", "rank_color": "#D864C7", "rank_text": "#000000",
  "tier_pct": 71, "rr": 47,
  "peak": "Immortal 1", "peak_delta": 2, "peak_act": "E7 · A2", "peak_hi": false,
  "stats": [ { "v": "1.34", "tone": "hi|normal|dim" }, … ],   // K/D, HS, WR, LVL — always 4
  "party_color": "#E34343",           // null = solo
  "anomaly": false,
  "recurrence": 2                     // 0 = none
}
```

Rules: **always 5 player entries per side is NOT required** — JS pads to 5 with ghost slots.
Every field is always present; `"N/A"` renders as a dimmed `—`, never a blank cell.

---

## 9. Module structure

```
gui/
  __init__.py     exports LoyalApp
  app.py          window lifecycle, poll thread, log fan-out, thread-safe JS push
  bridge.py       Api class exposed as pywebview js_api (JS → Python)
  derive.py       pure derivation (§7) — no webview import, headless-testable
  assets.py       agent portrait cache → base64 data URI (adapted from current assets.py)
  web/
    index.html    static shell: rail, assessment, two sides, footer
    app.css       tokens + all layout/motion
    app.js        renderer with diffed row updates, log ring buffer, icon cache
tests/
  test_derive.py  headless unit tests for §7
```

`gui/theme.py` and `gui/widgets.py` are deleted — their content moves to `app.css` and
`derive.py`. `constants.py` remains the single source of rank/party colour.

---

## 10. Integration contract

`main.py` **must not change.** `LoyalApp` keeps the surface it relies on:

| Method | Behaviour |
|---|---|
| `__init__()` | Creates the webview window immediately, showing `AWAITING RIOT CLIENT`. Never blank/frozen. |
| `after(delay_ms, fn)` | Compatibility shim — schedules `fn` via `threading.Timer`. `after(0, …)` runs promptly. |
| `mainloop()` | `webview.start()`. Blocks until the window closes. |
| `attach_backend(backend)` | Stores backend, populates the agent dropdown, starts polling. |
| `log_message(msg, tag)` | **Thread-safe from any thread.** Writes to `logging_setup.log_to_file` first, then pushes to JS. |

**Threading model**

- One daemon poll thread, 2s interval, calls the backend getters, builds the view model via
  `derive.build_view_model`, pushes with `evaluate_js`.
- All `evaluate_js` calls funnel through a single `_push(fn_name, payload)` helper guarded by a
  lock, which **queues into a `deque` until the DOM signals ready** (`api.ready()`), then flushes.
  This is the fix for the classic pywebview race where early log lines are lost.
- Button actions call blocking backend methods (`lock_agent`, `dodge_game`, `start_queue`,
  `force_update_data_from_gui`) on throwaway daemon threads — never on the webview thread.
- Every backend call is individually wrapped; one failing getter must not kill the poll loop.

**JS surface (Python → JS)**

`window.LOYAL.render(vm)` · `window.LOYAL.log(entry)` · `window.LOYAL.setAgents(list, selected)`
· `window.LOYAL.setIcon(agentName, dataUri)`

**Bridge surface (JS → Python), via `window.pywebview.api`**

`ready()` · `lock(agentName)` · `refresh()` · `dodge()` · `start_queue()` · `need_icons(names)`

**Diffed updates (non-negotiable).** `app.js` keeps `puuid → row element`. On render it updates
existing rows in place, creates only genuinely new ones, removes departed ones, and reorders
without rebuilding. No `innerHTML = ''` on the roster.

**Agent portraits.** Disk cache stays at `%APPDATA%/rankchecker/icon_cache`. JS reports unseen
agent names via `need_icons()`; Python loads/downloads on a background thread and pushes back a
base64 data URI, which JS caches in-process. Portraits are therefore never re-downloaded across
launches and never re-sent per poll tick.

### The one backend change (approved)

`app_backend.py` already computes `game_state` (`MENUS`/`PREGAME`/`INGAME`) inside
`_fetch_and_process_data` and discards it. Add:

```python
self._game_state = game_state          # store where it is already computed
def get_game_state_for_ui(self):       # read-only accessor on the integration seam
    return self._game_state
```

No logic changes. The UI falls back to inferring menus-vs-match from the player list if the
method is absent, so the two are decoupled.

---

## 11. Required states

| State | Rendering |
|---|---|
| No backend | `AWAITING RIOT CLIENT` placard, both sides all ghost slots, assessment hidden. |
| Menus | `MENUS` placard, **hostile side hidden entirely** (not empty), friendly shows party. |
| Agent select | Full screen as designed. |
| In match | As agent select, `MATCH LIVE` placard. |
| Stale >30s | `VALORANT OFFLINE` placard; last roster retained but dimmed. |
| Unranked / `"N/A"` | Dimmed `—`. Never a blank cell. Pill shows `UNRANKED` in `#2E2E2E`. |
| Backend getter raises | Logged as `error`, previous roster retained, poll loop survives. |

---

## 12. Out of scope

Always-on-top game overlay; file logging (`logging_setup.py` already owns it); any change to
backend business logic beyond the single accessor in §10; new rank-colour mappings.

---

## 13. Dependencies

Add to `requirements.txt`: `pywebview>=5.0`.
Remove: `customtkinter` (no longer imported anywhere).
`Pillow` is retained — `assets.py` still decodes portraits.

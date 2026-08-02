# Valorant Rank Yoinker — Fix & Finish Design

Date: 2026-07-28

## Context

`loyal-main` is an existing, partially-working Valorant Rank Yoinker spin-off (not a
greenfield project). It already has lockfile-based local API auth (`Request1.py`),
game-state handlers (`States/menu.py`, `States/pregame.py`, `States/coregame.py`),
enrichment modules (`rank.py`, `player_stats.py`, `names.py`, `content.py`), a backend
orchestrator (`app_backend.py`) with a background fetch thread, and a Tkinter/ttk
dark-themed GUI (`gui.py`). Discord RPC code exists (`rpc.py`) but is never
instantiated.

Investigation surfaced that the wiring between these pieces is broken in several
places, so despite the amount of code present, the app does not currently produce
correct data. This spec covers fixing that wiring, filling functional gaps (skin
info, pregame/coregame enrichment), wiring up Discord RPC, and rewriting the GUI in
CustomTkinter with a Team A (Friendly) / Team B (Enemy) split.

## Decision: fix-and-finish, not rebuild

Confirmed with user: keep the existing architecture and files, fix the bugs, extend
functionality, replace only `gui.py`. Do not restructure the module layout or start
a fresh project scaffold.

## Architecture

No structural change. Layers, unchanged:

- `Request1.py` — lockfile auth, header/token management, HTTP fetch wrapper.
- `States/menu.py`, `States/pregame.py`, `States/coregame.py` — per-game-state data
  handlers.
- `rank.py`, `player_stats.py`, `names.py`, `content.py` — enrichment modules.
- `presence.py` — local presence polling / game-state detection.
- `app_backend.py` — orchestrator; owns the background fetch thread and exposes
  getters the GUI reads from.
- `gui.py` — presentation layer (rewritten, see below).

New:

- `skins.py` — equipped-skin lookup for the highlighted weapon.
- `rpc.py` — kept, fixed, and wired into `app_backend.py` (previously dead code).
- `requirements.txt` — did not exist; added.

## Backend data-pipeline fixes

These are the confirmed root causes of the app currently returning wrong/empty data:

1. **Constructor mismatches** (`app_backend.py`):
   - `Rank(self.Requests, self.content, None)` must become
     `Rank(self.Requests, before_ascendant_seasons, self.content)` to match
     `Rank.__init__(self, Requests, ranks_before, Content)`. Currently `self.Content`
     inside `Rank` is `None`, breaking `get_act_episode_from_act_id` calls.
   - `Menu(self.Requests, self.rank)` must become `Menu(self.Requests, self.presences)`
     to match `Menu.__init__(self, Requests, presences)`.

2. **Key-name mismatch** between `Rank.get_rank()` output and what `app_backend.py`
   reads. `Rank` currently returns `rank` (tier int), `rr`, `leaderboard`, `peakrank`
   (tier int); `app_backend.py` reads `rank_name`, `rankedRating`, `leaderboardRank`,
   `peak_rank_name`, none of which exist. Fix: `Rank.get_rank()` resolves tier ints to
   display names via `NUMBERTORANKS` and returns the field names `app_backend.py`
   actually consumes. Update both sides to agree on one contract.

3. **Missing `win_rate`**: `player_stats.get_stats()` only returns `kd`/`hs`, but
   `app_backend.py` reads `ppstats['win_rate']`, which never exists — win rate is
   always `N/A`. `Rank.get_rank()` already computes win rate correctly (`wr` field)
   from season totals; reuse that instead of duplicating win-rate math in
   `player_stats.py`.

4. **Pregame/Coregame enrichment gap**: `States/pregame.py` and `States/coregame.py`
   currently return only `puuid`, `agent_id`, `team_id` per player — no name, rank,
   peak rank, RR, stats, or resolved agent name. This is the state that matters most
   (actual matches) and is currently the least complete. Fix: enrich each player
   entry in both handlers using `Names`, `Rank`, `PlayerStats`, and the `characters`
   dict (UUID → agent display name), and tag each with `team` (`ally`/`enemy`) so the
   GUI can split Friendly/Enemy.

5. **Content availability**: `Content.get_content()` is currently only called from
   the MENUS branch of `_fetch_and_process_data`, but `Rank` now depends on `Content`
   for peak-rank act/episode lookups in all states. Fix: fetch content once at
   backend init and refresh it periodically (e.g. once per N loop iterations or on a
   longer timer), not conditionally per game state.

## Skins

New `skins.py`, `Skins` class:

- Fetches the player's loadout via `/personalization/v2/players/{puuid}/playerloadout`
  (pd endpoint).
- Reads the highlighted weapon's skin socket (`constants.sockets["skin"]`) from the
  loadout, resolving skin UUID → display name via a bulk-fetched skins dict (cached
  at startup, same pattern as `Content.get_all_agents()`).
- Highlighted weapon defaults to `DEFAULT_CONFIG["weapon"]` (Vandal), matching the
  existing config default that's currently unused.
- Loadout is only fetchable for the local player and match participants during an
  active match — the "Skins Equipped" column will only populate in pregame/ingame
  states, `N/A` in menu state. This matches original Rank Yoinker behavior and is not
  a bug to fix.

## Discord RPC

- Instantiate `Rpc` in `ValorantRankYoinker.__init__`, gated behind
  `DEFAULT_CONFIG["flags"]["discord_rpc"]`.
- Call `rpc.set_rpc(presence)` each loop iteration in `_fetch_and_process_data`,
  after private presence is decoded.
- Fix existing typo in `rpc.py`: `large_imagee=` → `large_image=` in the in-game
  `self.rpc.update(...)` call — this currently silently breaks the Discord asset.

## GUI rewrite (CustomTkinter) — "Tactical Intel Readout"

`gui.py` is the centerpiece of this pass, not a skeleton to plug data into later.
Concept: the app reads like a scouting dossier pulled up during agent select, not a
themed dashboard — HUD/telemetry aesthetic, deliberately distinct from a literal
Valorant-brand reskin.

**Design tokens**

- Color: `#0B0E11` base, `#12171C` panel surface, `#232B32` hairline borders,
  `#3DDC97` signature accent (phosphor/night-vision green), `#E8484A` reserved only
  for Enemy-team framing, `#E7EDF0`/`#7C8791` text primary/secondary. Rank-tier
  colors reused as-is from `constants.py`'s `NUMBERTORANKS`/`tierDict`.
- Type: `Bahnschrift` (condensed grotesk, bundled with Windows 10/11) for
  headers/status labels, uppercase and tracked out. `Segoe UI` for names/body text.
  `Consolas` (monospace) for every numeric stat (RR, K/D, win rate) so stats read as
  a data terminal, not prose. Fall back to `Segoe UI`/system default if a font is
  unavailable (e.g. non-Windows) rather than erroring.
- Signature element — **the Threat Pill**: each player's rank badge renders as a
  pill filled with that rank's real tier color, with the RR number set in Consolas
  beside it. This is the one repeated, memorable device across every row — rank
  legible at a glance across ten players, which is the actual point of the tool.

**Layout**

- **Control bar** (top): agent dropdown + lock button, Refresh/Dodge/Start Queue as
  `CTkButton`/`CTkComboBox`, styled with the token system above (dark panel,
  phosphor-green accent on primary actions).
- **Status strip**: a pulsing LED-style dot (simple color-alternate via `after()`
  timer, green when connected) plus Bahnschrift-set status text — Connected/In
  Menus/In Pregame/In Match/Searching/Valorant Not Running/Waiting for Riot Client
  (red for error states).
- **Friendly | divider | Enemy** — two `CTkScrollableFrame` columns with a thin
  center divider (shows live score if available in match states). Each row is a
  compact intel card: agent thumbnail, party-color chip, name#tag, Threat Pill
  (rank + RR), small-caption peak rank, win rate/K-D, skin readout. In menu state
  (no enemy team) the Enemy column collapses and Friendly shows the party.
- **Party tags**: colored chip per party, reusing `PARTYICONLIST` colors from
  `constants.py` (converted from ANSI-style tuples to hex).
- **Log + Previously-Played-With**: collapse into a bottom drawer, closed by
  default (toggle to expand) — off-stage until wanted, so the roster owns the
  screen instead of competing with it.
- **Row updates are diffed**, not destroy-and-rebuild on every poll — updates
  individual cells/widgets in place. This both matches the "smooth interactions"
  goal and fixes the flicker the current full-table-rebuild approach causes.
- **Threading fix**: GUI updates move from the current raw background thread
  mutating Tkinter widgets (`_update_gui_loop`, a latent thread-safety bug) to
  Tkinter's `after()` polling loop on the main thread. The backend's own fetch
  thread is unaffected — this only changes how the GUI reads backend state.

**Assets**: agent portrait thumbnails pulled from `valorant-api.com` (agent
`displayIcon`), cached to disk on first fetch so repeat launches don't re-download.
No animation beyond the status LED pulse and diffed row updates — Tkinter has no
scroll/hover choreography to lean on, so motion stays minimal and functional.

## Error handling

- **Riot Client / Valorant not running**: `Request1.get_lockfile()`'s existing
  retry-with-backoff surfaces as a distinct "Waiting for Riot Client..." status-bar
  state instead of a silently frozen-looking UI.
- **Non-competitive / no season data**: `Rank.get_rank()` already degrades gracefully
  to a zeroed dict; GUI renders this as "Unranked/N/A" cleanly rather than blank
  cells.
- **Missing/expired token**: `Request1.py`'s `BAD_CLAIMS` retry and the unbounded
  `while True` loops in `get_lockfile`/`get_headers` get a max-retry cap with a
  clear status-bar error surfaced on exhaustion, instead of retrying forever
  silently.

## Packaging

New `requirements.txt`: `customtkinter`, `requests`, `pypresence`, `nest_asyncio`,
`colr`, `colorama`, `urllib3`.

## Explicitly out of scope

- No mock/offline data mode — user will verify against their live Valorant client.
- No .exe packaging.
- No config UI for `DEFAULT_CONFIG` flags — they stay code-level toggles for now.

## Verification

No live Valorant client available in the environment doing this work. Verification
will be: static/logic review of all changed files, confirming import graphs and
constructor signatures line up, and a dry run of anything mockable without a client
(e.g. constants, pure functions). The user will run the app against their live
client and report back anything still broken.

I need you to redesign the GUI for a Valorant companion desktop app called "Loyal" (a Valorant Rank Yoinker fork). You have full creative and technical freedom on visual direction and tech stack — including replacing the current CustomTkinter UI with a web-based stack (e.g. pywebview/Tauri-style embedded webview) if you think that gets a materially better result. The only hard constraint is that it has to run as a Windows desktop app launched from `main.py` and talk to the existing Python backend described below — don't touch backend/business logic, only the presentation layer and its integration seam.

## What the app does

It watches Valorant (via the local Riot Client API) and shows the current lobby — menus, agent select, or a live match — with each player's rank, peak rank, RR, K/D, headshot %, win rate, party grouping, and equipped skin. The entire point is a scout can glance at it during the ~40 seconds of agent select and read the lobby at a glance. Legibility and scan speed at a glance matter more than decoration.

## Current implementation (context, not a constraint to preserve)

- `gui/app.py` — CustomTkinter main window (`ValorantYoinkerGUI(ctk.CTk)`), polls the backend every 2s via `self.after(...)`, diffs the player list against on-screen cards instead of rebuilding.
- `gui/theme.py` — design tokens (colors, fonts, rank-color/party-color lookups).
- `gui/widgets.py` — `ThreatPill` (rank badge + RR) and `PlayerCard` (one player row).
- `gui/assets.py` — disk-cached agent portrait downloader.

Current visual direction is a dark "HUD/scouting-dossier" look (phosphor green `#3DDC97` accent, red `#E8484A` reserved for enemy framing, Bahnschrift headers, Consolas for stats) with two scrollable columns (Friendly | Enemy) and a collapsed-by-default log drawer at the bottom. You are not obligated to keep this direction — a full rethink of the aesthetic is welcome. Judge it on its own merits and propose something better if you see one.

## Backend integration contract (must preserve)

The GUI is constructed and attached to a backend asynchronously — `main.py` creates the GUI first (so the window appears immediately even if Valorant/Riot Client isn't running yet), then attaches a `ValorantRankYoinker` backend on a background thread once it's ready:

```python
app = ValorantYoinkerGUI()

def init_backend():
    backend = ValorantRankYoinker(status_callback=app.log_message)
    app.after(0, lambda: app.attach_backend(backend))

threading.Thread(target=init_backend, daemon=True).start()
app.mainloop()
```

Your GUI class needs to expose, at minimum, whatever the new equivalents of these are:
- A constructor that produces a usable window immediately, before any backend exists (must show a "waiting for Riot Client" state, not a blank/frozen window).
- `attach_backend(backend)` — called once the backend is ready.
- `log_message(message, tag="info")` — called from **background threads** (backend init, backend polling thread, RPC) as well as the main thread. Must be thread-safe with whatever UI toolkit you land on. `tag` is one of `info/warning/error/success/action/debug`.

The backend object (`app_backend.py`'s `ValorantRankYoinker`) exposes:
- `get_current_players_data_for_ui() -> list[dict]` — current lobby, see player dict shape below. Call this on a poll interval (currently 2s) from the UI side; the backend itself refreshes its internal snapshot on its own 10s thread, so faster UI polling just reads the same cached snapshot more often.
- `get_played_with_players_for_ui() -> list[str]` — human-readable "played with before" lines for the log/history area.
- `get_available_agents() -> list[str]` — for an agent-select dropdown.
- `lock_agent(agent_name: str)` — blocking call, run off the UI thread.
- `dodge_game()` — blocking call, run off the UI thread.
- `start_queue()` — blocking call, run off the UI thread.
- `force_update_data_from_gui()` — blocking call, run off the UI thread; triggers an immediate re-fetch instead of waiting for the backend's own 10s tick.

Player dict shape (from `player_format.py`, one entry per player in the lobby):
```python
{
    "puuid": str,
    "name": str, "tag": str,                 # Riot ID
    "rank": str, "rr": int,                  # e.g. "Diamond 2", 47
    "leaderboard_pos": int,                  # 0 if not on leaderboard
    "peak_rank": str,                        # e.g. "Immortal 1"
    "peak_rank_act": int | None, "peak_rank_ep": int | None,
    "kd": float | "N/A",
    "hs": int | "N/A",                       # headshot %, 0-100
    "wr": str,                               # e.g. "63%" or "N/A"
    "level": int | "N/A",                    # account level
    "agent": str,                            # display name, or "N/A (Menus)" outside a match
    "skins_equipped": str,                   # weapon skin display name, or "N/A"
    "party_index": int | None,               # for party-color grouping; None = solo
    "team": "friendly" | "enemy",
}
```
Rank names, rank tier colors (28 tiers, `constants.RANK_NAMES`/`RANK_COLORS_HEX`), and party chip colors (`constants.PARTY_COLORS_HEX`) already exist in `constants.py` — reuse them rather than inventing a new rank-color mapping.

Agent portrait images: currently fetched from `valorant-api.com` and disk-cached at `%APPDATA%/rankchecker/icon_cache` (see `gui/assets.py` for the existing pattern) — keep some form of this so portraits don't re-download every launch.

## Behavioral requirements (non-negotiable regardless of stack)

1. **Window appears immediately**, before the Riot Client connection exists — never a blank/frozen/white window during backend startup.
2. **Diffed updates, not full rebuilds.** The player list changes every 2-10s; whatever renders it must update in place, not flicker/rebuild the whole list every tick.
3. **Threading safety.** Backend calls and `log_message` arrive from background threads; all UI mutation must be marshaled onto the UI's own thread/event loop safely, however that toolkit does it.
4. **Friendly vs Enemy must be visually unambiguous** at a glance — this is the core job of the screen.
5. **Party grouping must be visible** per row (some existing color-chip mechanism).
6. **Graceful empty/error states**: "Waiting for Riot Client", "In Menus" (enemy side collapses/hides, not just empty), unranked/N-A stats rendered cleanly, not blank cells.
7. Controls needed somewhere in the UI: agent picker + Lock, Refresh, Dodge, Start Queue, and some log/history surface (doesn't need to be a bottom drawer — your call) showing recent status/log lines and "previously played with" callouts.
8. Every log line must still be viewable somewhere in the running app (a live log/console area) — file logging is handled separately in `logging_setup.py` and is out of scope.

## Deliverable

Give me:
1. A clear design direction and rationale (what changed from the current HUD look and why, or why you're keeping elements of it).
2. Your stack choice and why it's the right one for this (weigh: dev velocity, how much of the current Python backend integration friction it removes vs. adds, packaging/distribution as a Windows app, and whether it materially improves the "read the lobby in 40 seconds" goal).
3. A concrete component/file structure for the new `gui/` (or replacement) module.
4. Enough implementation to be a real starting point — not just a mockup description. If you pick something that isn't pure Python/Tk, be explicit about new dependencies, build/packaging implications, and exactly how `main.py`'s launch sequence and the `attach_backend`/`log_message`/polling contract above map onto the new toolkit.

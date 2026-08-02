"""
LoyalApp -- the pywebview host for the MAGI UI.

Replaces the CustomTkinter `ValorantYoinkerGUI` while keeping the exact
surface `main.py` depends on:

    app = LoyalApp()
    app.after(0, lambda: app.attach_backend(backend))   # from a worker thread
    app.mainloop()
    app.log_message("...", tag="info")

Threading model (see spec section 10):

* Every `evaluate_js` call funnels through the single `_push()` helper, which
  is guarded by one lock and **queues into a deque until the DOM signals
  ready** via `api.ready()`. Without the queue, everything pushed between
  `create_window()` and DOM-ready is silently dropped -- that includes all of
  the backend's constructor-time log lines, which is exactly when the
  interesting "waiting for the Riot lockfile" messages are emitted.
* One daemon poll thread at 2s. Each backend getter is wrapped individually so
  a single failing getter logs an error and leaves the loop alive.
* Blocking backend calls (lock/refresh/dodge/queue) run on throwaway daemon
  threads -- never on the webview thread.
"""

import json
import os
import sys
import threading
import time
from collections import deque

import webview

from logging_setup import log_to_file

POLL_INTERVAL_S = 2.0
STALE_DATA_TIMEOUT_S = 30.0

WINDOW_TITLE = "LOYAL // MAGI"
WINDOW_W = 1600
WINDOW_H = 640
BACKGROUND = "#07080A"

_FALLBACK_HTML = """
<!doctype html><html><head><meta charset="utf-8"><title>LOYAL</title>
<style>
 body{background:#07080A;color:#FF6B00;font-family:Consolas,monospace;padding:24px;margin:0}
 #log{color:#8B95A1;white-space:pre-wrap;font-size:12px;margin-top:16px}
</style></head><body>
<div>AWAITING RIOT CLIENT</div>
<div style="color:#FF2D3F;font-size:12px;margin-top:8px">gui/web/index.html not found</div>
<div id="log"></div>
<script>
 window.LOYAL = {
   render: function(){},
   setAgents: function(){},
   setIcon: function(){},
   log: function(e){ var d=document.getElementById('log');
     d.textContent += '[' + (e.tag||'info') + '] ' + (e.msg||'') + '\\n'; }
 };
 function go(){ if (window.pywebview && window.pywebview.api) { window.pywebview.api.ready(); }
   else { setTimeout(go, 50); } }
 go();
</script></body></html>
"""


def web_index_path():
    """Absolute path to gui/web/index.html, resolved from __file__ so it works
    regardless of cwd, and honouring PyInstaller's sys._MEIPASS unpack dir."""
    override = os.environ.get("LOYAL_WEB_INDEX")
    if override and os.path.isfile(override):
        return os.path.abspath(override)

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        bundled = os.path.join(meipass, "gui", "web", "index.html")
        if os.path.isfile(bundled):
            return bundled

    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "web", "index.html")


def _build_view_model(players, played_with, game_state, stale):
    """Delegate to gui.derive.build_view_model. Imported lazily so this module
    stays importable (and the window still opens) if derive is unavailable."""
    from gui.derive import build_view_model

    return build_view_model(players, played_with, game_state, stale)


def _minimal_view_model(state):
    """Last-resort view model so the window is never blank if derive blows up."""
    labels = {
        "AWAITING": ("AWAITING RIOT CLIENT", "NO BACKEND"),
        "MENUS": ("MENUS", "IDLE"),
        "PREGAME": ("AGENT SELECT", "PREGAME"),
        "INGAME": ("MATCH LIVE", "INGAME"),
        "OFFLINE": ("VALORANT OFFLINE", "STALE 30s"),
    }
    label, sub = labels.get(state, labels["AWAITING"])
    return {
        "state": state,
        "state_label": label,
        "state_sub": sub,
        "assessment": {"show": False},
        "flags": [],
        "sides": {
            "friendly": {"visible": True, "label": "", "players": []},
            "hostile": {"visible": state not in ("AWAITING", "MENUS"), "label": "", "players": []},
        },
    }


class LoyalApp:
    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def __init__(self):
        from gui.assets import AssetCache
        from gui.bridge import Api

        self.backend = None

        self._lock = threading.RLock()
        self._queue = deque()
        self._dom_ready = False
        self._closed = False

        self._players = []
        self._played_with = []
        self._last_data_ts = None
        self._attached_ts = None
        self._selected_agent = ""
        self._derive_warned = False

        self._assets = AssetCache()
        self.api = Api(self)

        self.window = webview.create_window(
            WINDOW_TITLE,
            url=self._resolve_url(),
            js_api=self.api,
            width=WINDOW_W,
            height=WINDOW_H,
            min_size=(900, 480),
            background_color=BACKGROUND,
            resizable=True,
            frameless=True,
            text_select=False,
        )

        try:
            self.window.events.closed += self._on_closed
        except Exception:
            pass

        # Queued -- flushes the instant the DOM reports ready.
        self._push("render", _minimal_view_model("AWAITING"))

        self._poll_thread = threading.Thread(
            target=self._poll_loop, name="loyal-poll", daemon=True
        )
        self._poll_thread.start()

        from logging_setup import get_log_path
        self.log_message(f"Logging to {get_log_path()}", tag="info")

    def _resolve_url(self):
        path = web_index_path()
        if os.path.isfile(path):
            return path
        log_to_file(f"gui/web/index.html not found at {path}; using fallback shell", "error")
        return None  # set via html= below

    def mainloop(self):
        """Blocks until the window is closed."""
        try:
            if self.window.original_url is None:
                self.window.load_html(_FALLBACK_HTML)
        except Exception:
            pass
        webview.start()
        self._closed = True

    def _on_closed(self):
        self._closed = True

    def after(self, delay_ms, fn):
        """Tk-compatibility shim. `after(0, fn)` must run promptly."""
        try:
            timer = threading.Timer(max(0.0, float(delay_ms) / 1000.0), self._run_safely, args=(fn,))
            timer.daemon = True
            timer.start()
            return timer
        except Exception as e:
            log_to_file(f"after() failed to schedule: {e}", "error")
            return None

    def _run_safely(self, fn):
        try:
            fn()
        except Exception as e:
            self.log_message(f"Scheduled callback failed: {e}", tag="error")

    # ------------------------------------------------------------------
    # The one JS push path
    # ------------------------------------------------------------------

    def _push(self, fn_name, *args):
        """The ONLY place evaluate_js is called. Serialised by self._lock and
        queued until the DOM signals ready, so nothing pushed during startup
        is lost."""
        try:
            encoded = ", ".join(
                json.dumps(a, ensure_ascii=False, default=str) for a in args
            )
        except Exception as e:
            log_to_file(f"_push: could not encode payload for {fn_name}: {e}", "error")
            return

        script = f"window.LOYAL && window.LOYAL.{fn_name}({encoded});"

        with self._lock:
            if self._closed:
                return
            if not self._dom_ready:
                # Bounded so a never-ready DOM cannot grow without limit.
                if len(self._queue) > 2000:
                    self._queue.popleft()
                self._queue.append(script)
                return
            self._eval(script)

    def _eval(self, script):
        # Caller holds self._lock.
        try:
            self.window.evaluate_js(script)
        except Exception as e:
            log_to_file(f"evaluate_js failed: {e}", "error")

    def _on_dom_ready(self):
        """Called from the bridge when app.js has built the DOM. Flushes the
        backlog in the order it was pushed."""
        with self._lock:
            self._dom_ready = True
            pending = list(self._queue)
            self._queue.clear()
            for script in pending:
                self._eval(script)
        if self.backend is not None:
            self._push_agents()

    # ------------------------------------------------------------------
    # Backend attach / logging (must work before a backend exists)
    # ------------------------------------------------------------------

    def attach_backend(self, backend):
        self.backend = backend
        try:
            backend.log_gui_callback = self.log_message
        except Exception:
            pass
        self._attached_ts = time.time()
        self._last_data_ts = time.time()
        self._push_agents()
        self.log_message("Backend attached.", tag="success")

    def _push_agents(self):
        if self.backend is None:
            return
        try:
            agents = self.backend.get_available_agents() or []
        except Exception as e:
            agents = []
            self.log_message(f"Error fetching agents for dropdown: {e}", tag="error")
        if agents and not self._selected_agent:
            self._selected_agent = agents[0]
        self._push("setAgents", agents, self._selected_agent)

    def log_message(self, message, tag="info"):
        """Thread-safe from any thread. Disk first (logging is already
        thread-safe and must not depend on the webview being alive), then JS."""
        try:
            log_to_file(message, tag)
        except Exception:
            pass
        try:
            self._push("log", {
                "ts": time.strftime("%H:%M:%S"),
                "tag": tag or "info",
                "msg": str(message),
            })
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Button actions -- blocking backend calls, each on its own daemon thread
    # ------------------------------------------------------------------

    def _spawn(self, fn, *args):
        def runner():
            try:
                fn(*args)
            except Exception as e:
                self.log_message(f"Action failed: {e}", tag="error")

        threading.Thread(target=runner, daemon=True).start()

    def _require_backend(self):
        if self.backend is None:
            self.log_message("Backend not ready yet.", tag="warning")
            return False
        return True

    def action_lock(self, agent_name=None):
        if agent_name:
            self._selected_agent = agent_name
        agent = self._selected_agent
        if not self._require_backend():
            return
        if not agent:
            self.log_message("No agent selected.", tag="warning")
            return
        self.log_message(f"Locking '{agent}'...", tag="action")
        self._spawn(self.backend.lock_agent, agent)

    def action_refresh(self):
        if not self._require_backend():
            return
        self.log_message("Refresh requested.", tag="action")
        self._spawn(self.backend.force_update_data_from_gui)

    def action_dodge(self):
        if not self._require_backend():
            return
        self.log_message("Dodge requested.", tag="action")
        self._spawn(self.backend.dodge_game)

    def action_start_queue(self):
        if not self._require_backend():
            return
        self.log_message("Start queue requested.", tag="action")
        self._spawn(self.backend.start_queue)

    # ------------------------------------------------------------------
    # Agent portraits
    # ------------------------------------------------------------------

    def request_icons(self, names):
        def on_ready(agent_name, data_uri):
            self._push("setIcon", agent_name, data_uri)

        try:
            self._assets.resolve_many(list(names or []), on_ready)
        except Exception as e:
            self.log_message(f"Icon resolve failed: {e}", tag="error")

    # ------------------------------------------------------------------
    # Poll loop -- one daemon thread, 2s, survives any single getter failing
    # ------------------------------------------------------------------

    def _poll_loop(self):
        while not self._closed:
            try:
                self._poll_once()
            except Exception as e:
                # Belt and braces: the loop must never die.
                try:
                    self.log_message(f"Poll error: {e}", tag="error")
                except Exception:
                    pass
            time.sleep(POLL_INTERVAL_S)

    def _is_stale(self):
        if self.backend is None or self._last_data_ts is None:
            return False
        return (time.time() - self._last_data_ts) > STALE_DATA_TIMEOUT_S

    def _poll_once(self):
        if self.backend is None:
            self._push("render", self._view_model([], [], None, False))
            return

        stale_before = self._is_stale()

        players = self._players
        try:
            fresh = self.backend.get_current_players_data_for_ui()
            if fresh:
                players = list(fresh)
                self._last_data_ts = time.time()
            elif not stale_before:
                players = list(fresh or [])
            # else: stale + empty -> retain the previous roster (dimmed by JS)
        except Exception as e:
            self.log_message(f"Error fetching player data: {e}", tag="error")

        played_with = self._played_with
        try:
            played_with = list(self.backend.get_played_with_players_for_ui() or [])
        except Exception as e:
            self.log_message(f"Error fetching played-with data: {e}", tag="error")

        game_state = None
        try:
            getter = getattr(self.backend, "get_game_state_for_ui", None)
            if callable(getter):
                game_state = getter()
        except Exception as e:
            self.log_message(f"Error fetching game state: {e}", tag="error")
            game_state = None

        if game_state not in ("MENUS", "PREGAME", "INGAME"):
            # Accessor absent or unresolved: infer menus-vs-match from the roster.
            if players:
                game_state = "INGAME" if any(
                    isinstance(p, dict) and p.get("team") == "enemy" for p in players
                ) else "MENUS"
            else:
                game_state = None

        self._players = players
        self._played_with = played_with

        stale = self._is_stale()
        self._push("render", self._view_model(players, played_with, game_state, stale))

    def _view_model(self, players, played_with, game_state, stale):
        try:
            return _build_view_model(players, played_with, game_state, stale)
        except Exception as e:
            if not self._derive_warned:
                self._derive_warned = True
                self.log_message(f"build_view_model unavailable ({e}); minimal render", tag="error")
            if stale:
                state = "OFFLINE"
            elif game_state in ("MENUS", "PREGAME", "INGAME"):
                state = game_state
            else:
                state = "AWAITING"
            return _minimal_view_model(state)


# Backwards-compatible alias -- main.py still constructs ValorantYoinkerGUI.
ValorantYoinkerGUI = LoyalApp

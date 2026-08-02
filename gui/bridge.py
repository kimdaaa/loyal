"""
JS -> Python bridge, exposed to the webview as `window.pywebview.api`.

Every method is wrapped in try/except and logs rather than propagating: an
exception thrown across the pywebview bridge surfaces as an opaque rejected
promise in JS with no Python traceback, which is miserable to debug.

The Api object holds a back-reference to the LoyalApp that owns it. All real
work is delegated to the app; nothing here blocks (the app runs blocking
backend calls on throwaway daemon threads).
"""


class Api:
    """js_api object handed to webview.create_window()."""

    def __init__(self, app):
        self._app = app

    # -- lifecycle -----------------------------------------------------

    def ready(self):
        """Called by app.js once the DOM is built and window.LOYAL exists.
        Releases the queued _push() backlog."""
        try:
            self._app._on_dom_ready()
            return True
        except Exception as e:
            self._safe_log(f"bridge.ready failed: {e}", "error")
            return False

    # -- actions -------------------------------------------------------

    def lock(self, agent=None):
        try:
            self._app.action_lock(agent)
            return True
        except Exception as e:
            self._safe_log(f"bridge.lock failed: {e}", "error")
            return False

    def refresh(self):
        try:
            self._app.action_refresh()
            return True
        except Exception as e:
            self._safe_log(f"bridge.refresh failed: {e}", "error")
            return False

    def dodge(self):
        try:
            self._app.action_dodge()
            return True
        except Exception as e:
            self._safe_log(f"bridge.dodge failed: {e}", "error")
            return False

    def start_queue(self):
        try:
            self._app.action_start_queue()
            return True
        except Exception as e:
            self._safe_log(f"bridge.start_queue failed: {e}", "error")
            return False

    def minimize(self):
        try:
            self._app.window.minimize()
            return True
        except Exception as e:
            self._safe_log(f"bridge.minimize failed: {e}", "error")
            return False

    def close(self):
        try:
            self._app.window.destroy()
            return True
        except Exception as e:
            self._safe_log(f"bridge.close failed: {e}", "error")
            return False

    # -- assets --------------------------------------------------------

    def need_icons(self, names=None):
        """JS reports agent names it has never seen. Each is resolved on a
        background thread; the app pushes setIcon(name, dataUri) back."""
        try:
            self._app.request_icons(names or [])
            return True
        except Exception as e:
            self._safe_log(f"bridge.need_icons failed: {e}", "error")
            return False

    # -- internals -----------------------------------------------------

    def _safe_log(self, message, tag):
        try:
            self._app.log_message(message, tag=tag)
        except Exception:
            pass

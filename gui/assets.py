"""
Async, disk-cached agent portrait loading -> base64 data URI.

Nothing in here blocks the UI thread: the agent-list fetch and per-icon
download/decode all happen on background daemon threads. Callers get the
data URI via a callback, or immediately (synchronously) if it is already
warm in the in-process memory cache.

Disk cache lives at %APPDATA%/rankchecker/icon_cache -- a portrait that has
been downloaded once is never downloaded again, across launches.
"""

import base64
import os
import re
import threading

import requests

AGENTS_ENDPOINT = "https://valorant-api.com/v1/agents?isPlayableCharacter=true"

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_-]+")


def _safe_filename(name):
    return _SAFE_NAME_RE.sub("_", name).strip("_") or "unknown"


def _to_data_uri(image_bytes):
    return "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii")


class AssetCache:
    """Fetches and caches agent portrait icons as `data:image/png;base64,...`
    strings.

    Usage:
        cache = AssetCache()
        uri = cache.get_icon("Jett", on_ready=lambda name, uri: ...)
        # uri is None if not ready yet; on_ready(agent_name, data_uri) fires
        # later from the worker thread, or the value is returned immediately
        # if already cached in memory.
    """

    def __init__(self, size=(33, 33)):
        self.size = size
        self._cache_dir = os.path.join(os.getenv("APPDATA") or ".", "rankchecker", "icon_cache")
        try:
            os.makedirs(self._cache_dir, exist_ok=True)
        except Exception:
            pass

        self._icon_urls = None  # {displayName: displayIconUrl}, lazily fetched once
        self._icon_urls_by_key = None  # {normalized displayName: displayIconUrl}
        self._icon_urls_lock = threading.Lock()

        self._image_cache = {}  # displayName -> data URI (in-memory, ready)
        self._pending = set()   # displayName currently being fetched/downloaded
        self._lock = threading.Lock()

    # -- public API ---------------------------------------------------

    def get_icon(self, agent_name, on_ready=None):
        """Return a cached data URI immediately if available, else kick off an
        async resolve (disk, then network, on a background thread) and call
        on_ready(agent_name, data_uri) once ready. Returns None if not
        immediately available. Never blocks."""
        if not agent_name:
            return None

        with self._lock:
            cached = self._image_cache.get(agent_name)
            if cached is not None:
                return cached
            if agent_name in self._pending:
                return None
            self._pending.add(agent_name)

        threading.Thread(
            target=self._load_icon_worker,
            args=(agent_name, on_ready),
            daemon=True,
        ).start()
        return None

    def resolve_many(self, agent_names, on_ready):
        """Resolve a batch of agent names. on_ready(name, data_uri) is invoked
        for each one that resolves -- immediately for in-memory hits, later
        from a worker thread otherwise."""
        for name in agent_names or []:
            try:
                cached = self.get_icon(name, on_ready=on_ready)
            except Exception:
                continue
            if cached is not None and on_ready is not None:
                try:
                    on_ready(name, cached)
                except Exception:
                    pass

    # -- internals ------------------------------------------------------

    def _ensure_icon_urls(self):
        """Populate self._icon_urls once (blocking network call) -- only ever
        called from a background thread."""
        with self._icon_urls_lock:
            if self._icon_urls is not None:
                return self._icon_urls
            try:
                resp = requests.get(AGENTS_ENDPOINT, timeout=10)
                resp.raise_for_status()
                data = resp.json().get("data", [])
                self._icon_urls = {
                    agent.get("displayName"): agent.get("displayIcon")
                    for agent in data
                    if agent.get("displayName")
                }
                self._icon_urls_by_key = {
                    agent.get("displayName").strip().lower(): agent.get("displayIcon")
                    for agent in data
                    if agent.get("displayName")
                }
            except Exception:
                self._icon_urls = {}
                self._icon_urls_by_key = {}
            return self._icon_urls

    def _load_icon_worker(self, agent_name, on_ready):
        try:
            data_uri = self._build_icon(agent_name)
        except Exception:
            data_uri = None

        with self._lock:
            self._pending.discard(agent_name)
            if data_uri is not None:
                self._image_cache[agent_name] = data_uri

        if data_uri is not None and on_ready is not None:
            try:
                on_ready(agent_name, data_uri)
            except Exception:
                pass

    def _build_icon(self, agent_name):
        normalized_name = str(agent_name or "").strip()
        if not normalized_name or normalized_name.lower().startswith("n/a"):
            return None

        cache_path = os.path.join(self._cache_dir, _safe_filename(normalized_name) + ".png")

        image_bytes = None
        if os.path.isfile(cache_path):
            try:
                with open(cache_path, "rb") as f:
                    image_bytes = f.read()
            except Exception:
                image_bytes = None

        if image_bytes is None:
            icon_urls = self._ensure_icon_urls()
            url = icon_urls.get(agent_name) or (self._icon_urls_by_key or {}).get(normalized_name.lower())
            if not url:
                return None
            try:
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                image_bytes = self._downscale(resp.content)
                with open(cache_path, "wb") as f:
                    f.write(image_bytes)
            except Exception:
                return None

        if not image_bytes:
            return None
        return _to_data_uri(image_bytes)

    def _downscale(self, image_bytes):
        """Shrink the downloaded portrait before it hits the disk cache so the
        data URI stays small. Pillow is optional here -- if it is missing or
        the decode fails, the original bytes are used verbatim."""
        try:
            from io import BytesIO
            from PIL import Image

            img = Image.open(BytesIO(image_bytes)).convert("RGBA")
            img.thumbnail((max(self.size) * 2, max(self.size) * 2), Image.LANCZOS)
            buf = BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return buf.getvalue()
        except Exception:
            return image_bytes

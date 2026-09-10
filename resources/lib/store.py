# -*- coding: utf-8 -*-
"""Local add-on data store (JSON), xbmc-free.

The caller supplies the concrete directory (under Kodi the add-on profile dir,
under the desktop tests a temp dir), so this module never imports xbmc* and can
be exercised without Kodi - matching resolver.py / ytlib.py.

Reads are tolerant on purpose: a missing, empty, corrupt or wrongly shaped file
is treated as "no data yet" instead of raising, so a damaged store never breaks
the UI. Writes are short and idempotent (load -> modify -> save).
"""

import json
import os
import time

SUBSCRIPTIONS_FILE = "subscriptions.json"
HISTORY_FILE = "history.json"

#: Watch history and search history share one file, each under its own key.
WATCH_KEY = "watch"
SEARCH_KEY = "searches"

#: Search history is bounded: the oldest query is dropped beyond this.
SEARCH_HISTORY_LIMIT = 20


def _number(value, default=None):
    """`value` as a float, or `default` when it is not a usable number."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class JsonStore(object):
    """A single JSON file living inside a caller-supplied directory."""

    def __init__(self, directory, filename):
        self.directory = directory or ""
        self.path = os.path.join(self.directory, filename) if self.directory else ""

    def ensure_directory(self):
        """Create the store directory; True when it exists afterwards."""
        if not self.directory:
            return False
        try:
            os.makedirs(self.directory, exist_ok=True)
        except OSError:
            return False
        return True

    def load(self, default):
        """Parsed JSON, or `default` when the file is missing/unreadable/invalid."""
        if not self.path:
            return default
        try:
            with open(self.path, "r", encoding="utf-8") as stream:
                return json.load(stream)
        except (OSError, ValueError):
            return default

    def save(self, data):
        """Write `data` atomically (temp file + rename); True on success."""
        if not self.ensure_directory():
            return False
        temp = self.path + ".tmp"
        try:
            with open(temp, "w", encoding="utf-8") as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            os.replace(temp, self.path)
        except (OSError, ValueError, TypeError):
            return False
        return True


class SubscriptionStore(object):
    """Channel subscriptions persisted as a JSON list of `channel_id` + name.

    A subscription is identified by its `channel_id` - subscribing an already
    stored channel updates its name instead of adding a duplicate. `list()`
    returns the channels newest-subscribed-first.
    """

    def __init__(self, directory, filename=SUBSCRIPTIONS_FILE):
        self._store = JsonStore(directory, filename)

    @property
    def path(self):
        """Concrete path of the backing file (empty when no directory was given)."""
        return self._store.path

    def ensure_directory(self):
        return self._store.ensure_directory()

    def _load(self):
        """Sanitized subscription list; never raises."""
        raw = self._store.load([])
        if not isinstance(raw, list):
            return []
        subscriptions = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            channel_id = entry.get("channel_id")
            if not channel_id:
                continue
            subscriptions.append({
                "channel_id": channel_id,
                "name": entry.get("name") or channel_id,
            })
        return subscriptions

    def list(self):
        """Stored channels, newest-subscribed first."""
        return self._load()

    def is_subscribed(self, channel_id):
        if not channel_id:
            return False
        return any(s["channel_id"] == channel_id for s in self._load())

    def subscribe(self, channel_id, name=None):
        """Add (or re-add) a channel at the front; True when persisted."""
        if not channel_id:
            return False
        others = [s for s in self._load() if s["channel_id"] != channel_id]
        others.insert(0, {"channel_id": channel_id, "name": name or channel_id})
        return self._store.save(others)

    def unsubscribe(self, channel_id):
        """Remove a channel; True when it is no longer subscribed afterwards."""
        if not channel_id:
            return False
        subscriptions = self._load()
        remaining = [s for s in subscriptions if s["channel_id"] != channel_id]
        if len(remaining) == len(subscriptions):
            return True  # already gone: idempotent success
        return self._store.save(remaining)


class _HistoryCollection(object):
    """One collection inside the shared history file, newest first.

    Watch history and search history live in the same JSON document under
    separate keys, so each collection is read and written on its own without
    touching the other (every write re-reads the document first). Ordering and
    deduplication are owned by this layer, which makes them testable without
    Kodi.
    """

    KEY = ""

    def __init__(self, directory, filename=HISTORY_FILE):
        self._store = JsonStore(directory, filename)

    @property
    def path(self):
        """Concrete path of the backing file (empty when no directory was given)."""
        return self._store.path

    def ensure_directory(self):
        return self._store.ensure_directory()

    def _document(self):
        """The whole history document; a wrongly shaped file counts as empty."""
        raw = self._store.load({})
        return raw if isinstance(raw, dict) else {}

    def list(self):
        """Stored entries, newest first; unusable entries are dropped."""
        entries = []
        for entry in self._document().get(self.KEY) or ():
            if not isinstance(entry, dict):
                continue
            sanitized = self._sanitize(entry)
            if sanitized is not None:
                entries.append(sanitized)
        return entries

    def _save(self, entries):
        """Persist this collection, leaving the other collections alone."""
        document = self._document()
        document[self.KEY] = entries
        return self._store.save(document)

    def _sanitize(self, entry):
        """A clean copy of `entry`, or None when it must be dropped."""
        raise NotImplementedError


class WatchHistoryStore(_HistoryCollection):
    """Watched videos, newest first, at most one entry per `video_id`.

    An entry carries the data needed to re-find and replay the video (`title`,
    `url`, `thumbnail`), its `duration`, a playback `position` in seconds
    (None until playback stops partway) and a `timestamp`. Recording a video
    that is already stored refreshes it and moves it back to the front instead
    of duplicating it.
    """

    KEY = WATCH_KEY

    def _sanitize(self, entry):
        video_id = entry.get("video_id")
        if not video_id:
            return None
        return {
            "video_id": video_id,
            "title": entry.get("title") or video_id,
            "url": entry.get("url") or "",
            "thumbnail": entry.get("thumbnail") or "",
            "duration": _number(entry.get("duration"), 0.0),
            "position": _number(entry.get("position")),
            "timestamp": _number(entry.get("timestamp"), 0.0),
        }

    def find(self, video_id):
        """The stored entry for `video_id`, or None when it is not watched."""
        if not video_id:
            return None
        for entry in self.list():
            if entry["video_id"] == video_id:
                return entry
        return None

    def record(self, video_id, title=None, url=None, thumbnail=None,
               duration=None, position=None):
        """Add (or refresh) a video at the front; True when persisted.

        A previously saved position is kept unless a new one is passed, so
        starting playback never loses the resume point before it is updated on
        stop. An already stored video moves back to the top instead of being
        duplicated.
        """
        if not video_id:
            return False
        previous = self.find(video_id) or {}
        entry = {
            "video_id": video_id,
            "title": title or previous.get("title") or video_id,
            "url": url or previous.get("url") or "",
            "thumbnail": thumbnail or previous.get("thumbnail") or "",
            "duration": _number(duration, _number(previous.get("duration"), 0.0)),
            "position": _number(position, _number(previous.get("position"))),
            "timestamp": time.time(),
        }
        others = [e for e in self.list() if e["video_id"] != video_id]
        others.insert(0, entry)
        return self._save(others)

    def set_position(self, video_id, position):
        """Store the playback position of an entry; True when persisted.

        At most one entry matches `video_id`. A missing entry, or a position
        that is not a usable number, leaves the store untouched.
        """
        seconds = _number(position)
        if not video_id or seconds is None or seconds < 0:
            return False
        entries = self.list()
        for entry in entries:
            if entry["video_id"] == video_id:
                entry["position"] = seconds
                return self._save(entries)
        return False

    def remove(self, video_id):
        """Drop one entry; True when it is gone afterwards (idempotent)."""
        if not video_id:
            return False
        entries = self.list()
        remaining = [e for e in entries if e["video_id"] != video_id]
        if len(remaining) == len(entries):
            return True
        return self._save(remaining)

    def clear(self):
        """Drop every entry; True when persisted."""
        return self._save([])


class SearchHistoryStore(_HistoryCollection):
    """Recent video search queries, newest first, deduplicated and capped."""

    KEY = SEARCH_KEY

    def __init__(self, directory, filename=HISTORY_FILE,
                 limit=SEARCH_HISTORY_LIMIT):
        _HistoryCollection.__init__(self, directory, filename)
        self.limit = limit

    def _sanitize(self, entry):
        query = entry.get("query")
        if not isinstance(query, str) or not query.strip():
            return None
        return {
            "query": query.strip(),
            "timestamp": _number(entry.get("timestamp"), 0.0),
        }

    def list_queries(self):
        """Stored queries, newest first."""
        return [entry["query"] for entry in self.list()]

    def record_query(self, query):
        """Store a query at the front; True when persisted.

        Repeating a stored query moves it to the front instead of adding a
        second copy, and the list is capped at `limit` by dropping the oldest
        queries. An empty query is not recorded.
        """
        text = (query or "").strip()
        if not text:
            return False
        entries = [e for e in self.list() if e["query"] != text]
        entries.insert(0, {"query": text, "timestamp": time.time()})
        return self._save(entries[:self.limit])

    def remove_query(self, query):
        """Drop one query; True when it is gone afterwards (idempotent)."""
        if not query:
            return False
        entries = self.list()
        remaining = [e for e in entries if e["query"] != query]
        if len(remaining) == len(entries):
            return True
        return self._save(remaining)

    def clear_queries(self):
        """Drop every query; True when persisted."""
        return self._save([])


__all__ = [
    "JsonStore",
    "SubscriptionStore",
    "WatchHistoryStore",
    "SearchHistoryStore",
    "SUBSCRIPTIONS_FILE",
    "HISTORY_FILE",
    "SEARCH_HISTORY_LIMIT",
]

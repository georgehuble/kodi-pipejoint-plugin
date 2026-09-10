# -*- coding: utf-8 -*-
"""Kodi-shim: subscriptions plumbing through default.py, fully offline.

The add-on profile directory is injected as a temp dir (getAddonInfo('profile'))
and ytlib is stubbed, so this runs exactly like Kodi would - but without Kodi
and without network. Covers the store path wiring, the channel page
Subscribe/Unsubscribe row, the toggle action and My subscriptions.

Usage:  python3 tests/test_kodi_shim_subscriptions.py
"""

import json
import os
import runpy
import shutil
import sys
import tempfile
import types
import urllib.parse
import xml.etree.ElementTree as ET

# Repo root = one level above tests/
ADDON_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Single source of truth: read the add-on id from the manifest (addon.xml).
ADDON_ID = ET.parse(os.path.join(ADDON_PATH, "addon.xml")).getroot().get("id")

CHANNEL_ID = "UCfakeChannel123"
CHANNEL_NAME = "Fake Channel"
SEPARATOR_LABELS = "-" * 16

FAKE_UPLOADS = [
    {"id": "vid1", "title": "Fake upload one", "description": "d1",
     "thumbnail": "", "duration": 120, "channel_id": CHANNEL_ID},
    {"id": "vid2", "title": "Fake upload two", "description": "d2",
     "thumbnail": "", "duration": 60, "channel_id": CHANNEL_ID},
]

state = {"items": [], "ended": False, "notifications": [], "profile": None,
         "uploads": None, "uploads_calls": []}
failures = []


def check(name, ok, detail=""):
    print("  [%s] %s%s" % ("OK" if ok else "FAIL", name,
                           (" - %s" % detail) if detail else ""))
    if not ok:
        failures.append(name)


class _InfoTag(object):
    def __init__(self):
        self.title = None
        self.plot = None
        self.duration = 0

    def setTitle(self, v): self.title = v
    def setPlot(self, v): self.plot = v
    def setDuration(self, v): self.duration = v


class _ListItem(object):
    def __init__(self, label=None, path=None, **kw):
        self.label = label
        self.path = path
        self.props = {}
        self.art = {}
        self.tag = _InfoTag()
        self.context_menu = []

    def setProperty(self, k, v): self.props[k] = v
    def setArt(self, d): self.art = d
    def getVideoInfoTag(self): return self.tag
    def addContextMenuItems(self, items, replaceItems=False):
        self.context_menu = list(items)


class _Dialog(object):
    def notification(self, *a, **k):
        state["notifications"].append(a)

    def input(self, *a, **k):
        return state.get("query", "")


def _modules():
    m = types.ModuleType("xbmc")
    m.LOGINFO = 1
    m.LOGERROR = 4
    m.LOGDEBUG = 0
    m.translatePath = lambda p: p
    m.log = lambda msg, level=1: None

    addon = types.ModuleType("xbmcaddon")
    addon.Addon = lambda: types.SimpleNamespace(
        getAddonInfo=lambda k: {"id": ADDON_ID,
                                "path": ADDON_PATH,
                                "profile": state["profile"]}[k],
        getSetting=lambda s: "0")

    gui = types.ModuleType("xbmcgui")
    gui.ListItem = _ListItem
    gui.Dialog = _Dialog
    gui.INPUT_ALPHANUM = 0
    gui.NOTIFICATION_ERROR = "error"
    gui.NOTIFICATION_WARNING = "warning"

    plugin = types.ModuleType("xbmcplugin")

    def addDirectoryItem(handle, url, item, isFolder=False):
        state["items"].append((url, item, isFolder))
        return True

    def endOfDirectory(handle, **k):
        state["ended"] = True

    plugin.addDirectoryItem = addDirectoryItem
    plugin.endOfDirectory = endOfDirectory
    plugin.setResolvedUrl = lambda *a, **k: state.update(resolved=a)
    plugin.setContent = lambda *a, **k: None

    catalog = types.ModuleType("ytlib")
    catalog.search = lambda query, limit=20: []
    catalog.search_channels = lambda query, limit=20: []

    def channel_uploads(channel_id, limit=50, offset=0):
        state["uploads_calls"].append((channel_id, limit, offset))
        videos = FAKE_UPLOADS if state["uploads"] is None else state["uploads"]
        return [dict(v) for v in videos[offset:offset + limit]]

    catalog.channel_uploads = channel_uploads

    return {"xbmc": m, "xbmcaddon": addon, "xbmcgui": gui,
            "xbmcplugin": plugin, "ytlib": catalog}


def run(query):
    """Run default.py like Kodi would for `query` (e.g. 'action=channel&...')."""
    state["items"] = []
    state["ended"] = False
    state["notifications"] = []
    sys.argv = ["plugin://%s/" % ADDON_ID, "1", "?" + query]
    for name, mod in _modules().items():
        sys.modules[name] = mod
    return runpy.run_path(ADDON_PATH + "/default.py", run_name="__main__")


def query_of(url):
    """Query params of a plugin:// url as a dict."""
    return dict(urllib.parse.parse_qsl(url.split("?", 1)[1]))


def action_of(url):
    return query_of(url).get("action")


def labels():
    return [item.label for _, item, _ in state["items"]]


def read_store(data_dir):
    path = os.path.join(data_dir, "subscriptions.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as stream:
        return json.load(stream)


def channel_query(name=CHANNEL_NAME):
    return urllib.parse.urlencode({"action": "channel",
                                   "channel_id": CHANNEL_ID,
                                   "name": name})


def main():
    profile = tempfile.mkdtemp(prefix="pipejoint-shim-")
    data_dir = os.path.join(profile, "addon_data")
    state["profile"] = data_dir
    try:
        print("=== 2.1 store path wiring ===")
        globs = run("")
        check("main menu rendered", state["ended"] and state["items"],
              "%d item(s)" % len(state["items"]))
        check("data_dir() uses the injected profile",
              globs["data_dir"]() == data_dir, globs["data_dir"]())
        db = globs["get_store"]()
        check("store constructed on the injected path",
              db is not None and db.path == os.path.join(data_dir, "subscriptions.json"),
              getattr(db, "path", None))
        check("store directory created", os.path.isdir(data_dir), data_dir)
        check("store starts empty", db.list() == [])

        print("=== 3.1 channel page: action row, divider, uploads ===")
        run(channel_query())
        check("page rendered", state["ended"] and len(state["items"]) == len(FAKE_UPLOADS) + 2,
              "%d item(s)" % len(state["items"]))
        check("first row is the Subscribe action", labels()[:1] == ["Subscribe"],
              repr(labels()))
        toggle_url = state["items"][0][0]
        toggle_qs = query_of(toggle_url)
        check("action row targets toggle_subscription",
              toggle_qs.get("action") == "toggle_subscription", toggle_url)
        check("action row carries the channel id",
              toggle_qs.get("channel_id") == CHANNEL_ID, toggle_url)
        check("action row carries the channel name",
              toggle_qs.get("name") == CHANNEL_NAME, toggle_url)
        check("action row is a folder (selectable)",
              state["items"][0][2] is True)
        check("divider follows the action row",
              labels()[1:2] == [SEPARATOR_LABELS] and action_of(state["items"][1][0]) == "noop",
              repr(labels()[1:2]))
        check("divider is not a folder", state["items"][1][2] is False)
        check("uploads follow the divider",
              [item.tag.title for _, item, _ in state["items"][2:]] ==
              [u["title"] for u in FAKE_UPLOADS], repr(labels()[2:]))
        check("uploads are playable, not folders",
              all(folder is False for _, _, folder in state["items"][2:]))

        print("=== 3.2 toggle subscribes and reflects the new state ===")
        run(toggle_url.split("?", 1)[1])
        stored = read_store(data_dir)
        check("subscription written to the store",
              stored == [{"channel_id": CHANNEL_ID, "name": CHANNEL_NAME}], repr(stored))
        check("page reopened with the Unsubscribe action",
              labels()[:1] == ["Unsubscribe"], repr(labels()[:1]))
        check("uploads still follow the action",
              len(state["items"]) == len(FAKE_UPLOADS) + 2)
        check("toggled row still targets toggle_subscription",
              action_of(state["items"][0][0]) == "toggle_subscription")

        print("=== 3.2 toggle again unsubscribes ===")
        run(state["items"][0][0].split("?", 1)[1])
        check("store emptied", read_store(data_dir) == [], repr(read_store(data_dir)))
        check("page reopened with the Subscribe action",
              labels()[:1] == ["Subscribe"], repr(labels()[:1]))

        print("=== 3.4 channel page paginates the long video list ===")
        state["uploads"] = [
            dict(u, id="page%04d" % i, title="Video %04d" % i)
            for i, u in enumerate(FAKE_UPLOADS * 25)          # a full 50 videos
        ]
        run(channel_query())
        check("a full page adds the More videos row",
              labels()[-1:] == ["More videos..."], repr(labels()[-3:]))
        check("page holds 50 videos between the action and the More row",
              len(state["items"]) == 50 + 2 + 1,
              "%d item(s)" % len(state["items"]))
        more = query_of(state["items"][-1][0])
        check("More videos reopens the channel at the next offset",
              more.get("action") == "channel" and more.get("channel_id") == CHANNEL_ID
              and more.get("offset") == "50", repr(more))
        check("More videos keeps the channel name", more.get("name") == CHANNEL_NAME,
              repr(more))

        run(channel_query() + "&offset=50")
        check("the next page asks for offset 50",
              state["uploads_calls"][-1] == (CHANNEL_ID, 50, 50),
              repr(state["uploads_calls"][-1]))

        state["uploads"] = None
        run(channel_query())
        check("a short page has no More videos row",
              "More videos..." not in labels(), repr(labels()))

        print("=== 4.1 My subscriptions ===")
        run("action=subscriptions")
        check("empty store lists nothing", state["items"] == [])
        check("empty store informs the user", bool(state["notifications"]),
              repr(state["notifications"]))
        check("directory still closed", state["ended"] is True)

        run(channel_query())                      # open the channel page again
        run(toggle_url.split("?", 1)[1])          # ... and subscribe from it
        run("action=subscriptions")
        check("subscribed channel listed once", len(state["items"]) == 1,
              "%d item(s)" % len(state["items"]))
        check("row label is the channel name", labels() == [CHANNEL_NAME], repr(labels()))
        row_url = state["items"][0][0]
        check("row targets the channel action",
              action_of(row_url) == "channel", row_url)
        check("row carries the channel id",
              query_of(row_url).get("channel_id") == CHANNEL_ID, row_url)
        check("row is a folder", state["items"][0][2] is True)

        run(state["items"][0][0].split("?", 1)[1])   # open it, then unsubscribe
        run(state["items"][0][0].split("?", 1)[1])
        run("action=subscriptions")
        check("unsubscribed channel disappears", state["items"] == [],
              repr(labels()))

        print("=== 4.2 main menu ===")
        run("")
        check("menu lists the four entries",
              labels() == ["Search videos", "Search channels", "Watch history",
                           "My subscriptions"],
              repr(labels()))
        check("menu actions wired to the router",
              [action_of(url) for url, _, _ in state["items"]] ==
              ["new_search", "search_channels", "watch_history", "subscriptions"])
        check("menu entries are folders",
              all(folder for _, _, folder in state["items"]))
        check("menu closed the directory", state["ended"] is True)
    finally:
        shutil.rmtree(profile, ignore_errors=True)

    if failures:
        print("RESULT: FAIL (%d check(s): %s)" % (len(failures), ", ".join(failures)))
        sys.exit(1)
    print("RESULT: OK (store wired, channel page action row and My subscriptions)")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Kodi-shim: the video-search flow with a local query history, offline.

The add-on profile is injected as a temp dir and ytlib is stubbed, so the router
runs exactly as Kodi would - but without Kodi and without network. Covers change
tasks 4.1 (recent queries + New search..., recording each performed search) and
4.2 (re-selecting a past query, removing one entry, clearing all).

Usage:  python3 tests/test_kodi_shim_search_history.py
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

sys.path.insert(0, os.path.join(ADDON_PATH, "resources", "lib"))

import store  # noqa: E402

NEW_SEARCH_LABEL = "New search..."
REMOVE_QUERY_LABEL = "Remove from search history"
CLEAR_QUERIES_LABEL = "Clear search history"

FAKE_VIDEOS = [
    {"id": "aaa111", "title": "Fake video one", "description": "d1",
     "thumbnail": "", "duration": 120},
    {"id": "bbb222", "title": "Fake video two", "description": "d2",
     "thumbnail": "", "duration": 60},
]

state = {"items": [], "ended": False, "notifications": [], "profile": None,
         "query": "", "asked": [], "searches": [], "channel_searches": [],
         "results": None}

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
        state["asked"].append(a)
        return state["query"]


def _fake_ytlib():
    m = types.ModuleType("ytlib")

    def search(query, limit=20):
        state["searches"].append(query)
        videos = FAKE_VIDEOS if state["results"] is None else state["results"]
        return [dict(v) for v in videos][:limit]

    def search_channels(query, limit=20):
        state["channel_searches"].append(query)
        return []

    m.search = search
    m.search_channels = search_channels
    m.channel_uploads = lambda channel_id, limit=50, offset=0: []
    return m


def _modules():
    m = types.ModuleType("xbmc")
    m.LOGINFO = 1
    m.LOGERROR = 4
    m.LOGDEBUG = 0
    m.translatePath = lambda p: p
    m.log = lambda msg, level=1: None

    addon = types.ModuleType("xbmcaddon")
    addon.Addon = lambda: types.SimpleNamespace(
        getAddonInfo=lambda k: {"id": ADDON_ID, "path": ADDON_PATH,
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

    plugin.addDirectoryItem = addDirectoryItem
    plugin.endOfDirectory = lambda handle, **k: state.update(ended=True)
    plugin.setResolvedUrl = lambda *a, **k: None
    plugin.setContent = lambda *a, **k: None

    return {"xbmc": m, "xbmcaddon": addon, "xbmcgui": gui,
            "xbmcplugin": plugin, "ytlib": _fake_ytlib()}


def run(action_url, query=None, results=None):
    """Run default.py like Kodi would for `action_url` (e.g. 'action=new_search')."""
    state["items"] = []
    state["ended"] = False
    state["notifications"] = []
    state["asked"] = []
    state["searches"] = []
    state["channel_searches"] = []
    state["results"] = results
    if query is not None:
        state["query"] = query
    sys.argv = ["plugin://%s/" % ADDON_ID, "1", "?" + action_url]
    for name, mod in _modules().items():
        sys.modules[name] = mod
    return runpy.run_path(ADDON_PATH + "/default.py", run_name="__main__")


def query_of(url):
    return dict(urllib.parse.parse_qsl(url.split("?", 1)[1]))


def labels():
    return [item.label for _, item, _ in state["items"]]


def stored_queries(data_dir):
    path = os.path.join(data_dir, "history.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as stream:
        document = json.load(stream)
    return [entry["query"] for entry in document.get("searches") or []]


def main():
    profile = tempfile.mkdtemp(prefix="pipejoint-search-shim-")
    data_dir = os.path.join(profile, "addon_data")
    state["profile"] = data_dir
    try:
        # --- 4.1 showing recent queries + New search... ----------------------
        print("=== 4.1 an empty search history shows only New search... ===")
        run("action=new_search")
        check("only the New search action is listed", labels() == [NEW_SEARCH_LABEL],
              repr(labels()))
        check("the action opens the query prompt",
              query_of(state["items"][0][0]).get("action") == "search_input",
              state["items"][0][0])
        check("the action is a folder", state["items"][0][2] is True)
        check("directory closed", state["ended"] is True)
        check("nothing stored yet", stored_queries(data_dir) == [],
              repr(stored_queries(data_dir)))

        print("=== 4.1 performing a search records the query ===")
        run("action=search_input", query="kodi tips")
        check("the prompt was shown", bool(state["asked"]), repr(state["asked"]))
        check("the catalog got the query", state["searches"] == ["kodi tips"],
              repr(state["searches"]))
        check("results rendered",
              [item.tag.title for _, item, _ in state["items"]] ==
              [v["title"] for v in FAKE_VIDEOS], repr(labels()))
        check("query stored", stored_queries(data_dir) == ["kodi tips"],
              repr(stored_queries(data_dir)))

        print("=== 4.1 a cancelled prompt searches and records nothing ===")
        run("action=search_input", query="")
        check("no query stored", stored_queries(data_dir) == ["kodi tips"],
              repr(stored_queries(data_dir)))
        check("catalog not queried", state["searches"] == [], repr(state["searches"]))
        check("nothing rendered", state["items"] == [], repr(labels()))

        print("=== 4.1 New search... stays on top, queries follow newest-first ===")
        run("action=results&q=linux")
        run("action=new_search")
        check("New search... is pinned to the top",
              labels() == [NEW_SEARCH_LABEL, "linux", "kodi tips"], repr(labels()))
        check("the pinned row opens the query prompt",
              query_of(state["items"][0][0]).get("action") == "search_input",
              state["items"][0][0])
        check("query rows re-run the search",
              [query_of(url).get("action") for url, _, _ in state["items"]] ==
              ["search_input", "results", "results"], repr(labels()))
        check("query rows carry their query",
              [query_of(url).get("q") for url, _, _ in state["items"]][1:] ==
              ["linux", "kodi tips"], repr(labels()))
        check("query rows are folders",
              all(folder for _, _, folder in state["items"][1:]))

        print("=== 4.1 repeating a query moves it to the top (no duplicate) ===")
        run("action=results&q=kodi%20tips")
        check("moved to the top", stored_queries(data_dir) == ["kodi tips", "linux"],
              repr(stored_queries(data_dir)))
        check("no duplicate", len(stored_queries(data_dir)) == 2,
              repr(stored_queries(data_dir)))

        print("=== 4.1 a channel search is not recorded ===")
        before = stored_queries(data_dir)
        run("action=search_channels", query="some channel")
        check("channel search ran", state["channel_searches"] == ["some channel"],
              repr(state["channel_searches"]))
        check("search history unchanged", stored_queries(data_dir) == before,
              repr(stored_queries(data_dir)))

        # --- 4.2 re-running, removing, clearing -------------------------------
        print("=== 4.2 selecting a past query re-runs that search ===")
        run("action=new_search")
        select = state["items"][1][0].split("?", 1)[1]        # action=results&q=...
        run(select)
        check("the stored query was searched", state["searches"] == ["kodi tips"],
              repr(state["searches"]))
        check("results rendered", len(state["items"]) == len(FAKE_VIDEOS),
              repr(labels()))
        check("re-running keeps it at the top",
              stored_queries(data_dir) == ["kodi tips", "linux"],
              repr(stored_queries(data_dir)))

        print("=== 4.2 the context menu offers remove and clear ===")
        run("action=new_search")
        ctx = dict(state["items"][1][1].context_menu)     # first query row
        check("remove entry present", REMOVE_QUERY_LABEL in ctx, repr(ctx))
        check("clear entry present", CLEAR_QUERIES_LABEL in ctx, repr(ctx))
        remove_url = ctx[REMOVE_QUERY_LABEL]
        check("remove targets remove_query with the query",
              query_of(remove_url).get("action") == "remove_query"
              and query_of(remove_url).get("q") == "kodi tips", remove_url)
        check("clear targets clear_queries",
              query_of(ctx[CLEAR_QUERIES_LABEL]).get("action") == "clear_queries",
              ctx[CLEAR_QUERIES_LABEL])

        print("=== 4.2 removing one query ===")
        run(remove_url.split("?", 1)[1])
        check("query removed", stored_queries(data_dir) == ["linux"],
              repr(stored_queries(data_dir)))
        check("flow reopened with New search... on top and the remaining query",
              labels() == [NEW_SEARCH_LABEL, "linux"], repr(labels()))

        print("=== 4.2 clearing the search history ===")
        run("action=clear_queries")
        check("history emptied", stored_queries(data_dir) == [],
              repr(stored_queries(data_dir)))
        check("empty flow shows New search...", labels() == [NEW_SEARCH_LABEL],
              repr(labels()))

        print("=== 4.2 the flow stays within the store limit ===")
        for index in range(store.SEARCH_HISTORY_LIMIT + 2):
            run("action=results&q=%s"
                % urllib.parse.quote_plus("query %02d" % index))
        run("action=new_search")
        check("at most the stored limit is listed",
              len(state["items"]) == store.SEARCH_HISTORY_LIMIT + 1,
              "%d item(s)" % len(state["items"]))
        check("New search... stays first", labels()[0] == NEW_SEARCH_LABEL,
              repr(labels()[:3]))
        check("the newest query follows it", labels()[1] == "query 21",
              repr(labels()[:3]))
        check("the oldest queries were dropped",
              "query 00" not in labels() and "query 01" not in labels(),
              repr(labels()[-3:]))

        print("=== 4.2 a search without results is still a performed search ===")
        run("action=results&q=nothing%20at%20all", results=[])
        check("query recorded", "nothing at all" in stored_queries(data_dir),
              repr(stored_queries(data_dir)))
        check("user informed about no results", bool(state["notifications"]),
              repr(state["notifications"]))

        print("=== 4.2 the search flow needs no store to keep working ===")
        state["profile"] = None
        run("action=new_search")
        check("flow still renders New search...", labels() == [NEW_SEARCH_LABEL],
              repr(labels()))
        run("action=results&q=offline")
        check("results still render", len(state["items"]) == len(FAKE_VIDEOS),
              repr(labels()))
        state["profile"] = data_dir
    finally:
        shutil.rmtree(profile, ignore_errors=True)

    if failures:
        print("RESULT: FAIL (%d check(s): %s)" % (len(failures), ", ".join(failures)))
        sys.exit(1)
    print("RESULT: OK (video search history shown, recorded, re-run, removed, cleared)")


if __name__ == "__main__":
    main()

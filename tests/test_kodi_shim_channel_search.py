# -*- coding: utf-8 -*-
"""Kodi-shim: the Search channels router action, offline.

ytlib is stubbed (no network) and the search dialog is answered from `state`,
so default.py can be run exactly as Kodi would.

Usage:  python3 tests/test_kodi_shim_channel_search.py
"""

import os
import runpy
import sys
import types
import urllib.parse
import xml.etree.ElementTree as ET

# Repo root = one level above tests/
ADDON_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Single source of truth: read the add-on id from the manifest (addon.xml).
ADDON_ID = ET.parse(os.path.join(ADDON_PATH, "addon.xml")).getroot().get("id")

FAKE_CHANNELS = [
    {"channel_id": "UCfake0001", "name": "Fake Channel One",
     "url": "https://www.youtube.com/channel/UCfake0001",
     "thumbnail": "https://yt3.googleusercontent.com/one.png"},
    {"channel_id": "UCfake0002", "name": "Fake Channel Two",
     "url": "https://www.youtube.com/channel/UCfake0002", "thumbnail": ""},
]

state = {"items": [], "ended": False, "notifications": [], "query": "kodi",
         "results": None, "asked": []}
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


def _modules():
    m = types.ModuleType("xbmc")
    m.LOGINFO = 1
    m.LOGERROR = 4
    m.LOGDEBUG = 0
    m.translatePath = lambda p: p
    m.log = lambda msg, level=1: None

    addon = types.ModuleType("xbmcaddon")
    addon.Addon = lambda: types.SimpleNamespace(
        getAddonInfo=lambda k: {"id": ADDON_ID, "path": ADDON_PATH}[k],
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

    catalog = types.ModuleType("ytlib")
    catalog.search = lambda query, limit=20: []
    catalog.channel_uploads = lambda cid, limit=20: []

    def search_channels(query, limit=20):
        state["searched"] = query
        results = state["results"]
        return [] if results is None else [dict(c) for c in results][:limit]

    catalog.search_channels = search_channels

    return {"xbmc": m, "xbmcaddon": addon, "xbmcgui": gui,
            "xbmcplugin": plugin, "ytlib": catalog}


def run(action_url, query=None, results=None):
    state["items"] = []
    state["ended"] = False
    state["notifications"] = []
    state["asked"] = []
    state["searched"] = None
    if query is not None:
        state["query"] = query
    state["results"] = results
    sys.argv = ["plugin://%s/" % ADDON_ID, "1", "?" + action_url]
    for name, mod in _modules().items():
        sys.modules[name] = mod
    return runpy.run_path(ADDON_PATH + "/default.py", run_name="__main__")


def query_of(url):
    return dict(urllib.parse.parse_qsl(url.split("?", 1)[1]))


def main():
    print("=== 5.3 channel search results ===")
    run("action=search_channels", query="kodi", results=FAKE_CHANNELS)
    check("the query is asked for", bool(state["asked"]), repr(state["asked"]))
    check("the catalog got the query", state["searched"] == "kodi",
          repr(state["searched"]))
    check("one row per channel", len(state["items"]) == len(FAKE_CHANNELS),
          "%d item(s)" % len(state["items"]))
    check("rows are labelled with the channel name",
          [item.label for _, item, _ in state["items"]] ==
          ["Fake Channel One", "Fake Channel Two"],
          repr([item.label for _, item, _ in state["items"]]))
    check("rows are folders", all(folder for _, _, folder in state["items"]))
    check("directory closed", state["ended"] is True)

    for (url, item, _), channel in zip(state["items"], FAKE_CHANNELS):
        qs = query_of(url)
        check("row %s targets the channel action" % channel["channel_id"],
              qs.get("action") == "channel", url)
        check("row %s carries the channel id" % channel["channel_id"],
              qs.get("channel_id") == channel["channel_id"], url)
        check("row %s carries the channel name" % channel["channel_id"],
              qs.get("name") == channel["name"], url)
    check("thumbnail art is passed through when available",
          state["items"][0][1].art.get("thumb") == FAKE_CHANNELS[0]["thumbnail"],
          repr(state["items"][0][1].art))

    print("=== 5.3 opening a result reaches the channel page ===")
    submit = state["items"][0][0].split("?", 1)[1]
    run(submit, results=FAKE_CHANNELS)
    check("channel page shown with its subscribe row",
          [item.label for _, item, _ in state["items"]][:1] == ["Subscribe"],
          repr([item.label for _, item, _ in state["items"]]))
    check("subscribe row toggles the channel from the result",
          query_of(state["items"][0][0]).get("channel_id") ==
          FAKE_CHANNELS[0]["channel_id"],
          state["items"][0][0])

    print("=== 5.3 no matches informs the user ===")
    run("action=search_channels", query="nothing at all", results=[])
    check("no rows rendered", state["items"] == [], repr(state["items"]))
    check("user informed about no channels", bool(state["notifications"]),
          repr(state["notifications"]))
    check("directory still closed", state["ended"] is True)

    print("=== 5.3 a cancelled prompt renders nothing ===")
    run("action=search_channels", query="", results=FAKE_CHANNELS)
    check("no rows rendered", state["items"] == [], repr(state["items"]))
    check("catalog not queried", state["searched"] is None, repr(state["searched"]))

    if failures:
        print("RESULT: FAIL (%d check(s): %s)" % (len(failures), ", ".join(failures)))
        sys.exit(1)
    print("RESULT: OK (Search channels renders channel rows -> channel action)")


if __name__ == "__main__":
    main()

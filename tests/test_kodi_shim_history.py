# -*- coding: utf-8 -*-
"""Kodi-shim: watch-history recording and the player-monitor seam, offline.

The add-on profile is injected as a temp dir, ytlib/resolver are stubbed and
`xbmc.Player` is a scripted fake, so the router can be run exactly as Kodi
would - but without Kodi and without network. Covers change tasks 2.1 (record
on play start) and 2.2 (player observation saves the stop position).

Usage:  python3 tests/test_kodi_shim_history.py
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

import player_monitor  # noqa: E402
import store  # noqa: E402

VID1 = "vidAAAAAAAA"
VID2 = "vidBBBBBBBB"
VID3 = "vidCCCCCCCC"
WATCH_URL = "https://www.youtube.com/watch?v=%s"
HLS_URL = "https://cdn.example/master.m3u8"
WATCH_HISTORY_ACTION = "watch_history"

state = {"items": [], "ended": False, "notifications": [], "profile": None,
         "resolved": [], "player": None, "query": "", "select_return": -1,
         "asked": [], "selected": [], "searches": []}

failures = []


def check(name, ok, detail=""):
    print("  [%s] %s%s" % ("OK" if ok else "FAIL", name,
                           (" - %s" % detail) if detail else ""))
    if not ok:
        failures.append(name)


# --- stubs ------------------------------------------------------------------

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

    def setContentLookup(self, v): self.content_lookup = v
    def setMimeType(self, v): self.mime = v
    def setProperty(self, k, v): self.props[k] = v
    def setArt(self, d): self.art = d
    def getVideoInfoTag(self): return self.tag
    def setSubtitles(self, urls): self.subtitles = list(urls)
    def addContextMenuItems(self, items, replaceItems=False):
        self.context_menu = list(items)


class _Dialog(object):
    def notification(self, *a, **k):
        state["notifications"].append(a)

    def input(self, *a, **k):
        state["asked"].append(a)
        return state["query"]

    def select(self, heading, options):
        state["selected"].append((heading, list(options)))
        return state["select_return"]


class _Monitor(object):
    """Kodi's abort monitor: never aborts, so the polls return immediately."""

    def waitForAbort(self, seconds):
        return False


class _FakePlayer(object):
    """Player whose `isPlaying()` answers from a script and `getTime()` too."""

    def __init__(self, playing, times=None, time_error=False):
        self.script = list(playing)
        self.times = list(times or [])
        self.time_error = time_error
        self.waits = 0

    def isPlaying(self):
        if self.script:
            return self.script.pop(0)
        return False

    def getTime(self):
        if self.time_error:
            raise RuntimeError("player has no time")
        if self.times:
            return self.times.pop(0)
        return 0.0


def _info(video_id):
    return {
        "id": video_id,
        "title": "Fake title %s" % video_id,
        "description": "Fake desc",
        "duration": 300,
        "thumbnail": "https://t/thumb.png",
        "webpage_url": WATCH_URL % video_id,
        "formats": [
            {"protocol": "https", "vcodec": "avc1", "acodec": "mp4a",
             "height": 720, "url": "https://prog.example/720.mp4"},
            {"protocol": "m3u8_native", "vcodec": "avc1", "acodec": "none",
             "height": 720, "url": HLS_URL, "manifest_url": HLS_URL,
             "http_headers": {"User-Agent": "ua"}},
        ],
    }


def _fake_resolver():
    m = types.ModuleType("resolver")
    m.HLS_MIME = "application/vnd.apple.mpegurl"

    def resolve_video(video_id, allow_progressive=True, max_height=None):
        return "hls", HLS_URL, {"User-Agent": "ua"}, _info(video_id)

    def available_heights(info):
        return sorted({int(f["height"]) for f in info.get("formats") or ()
                       if f.get("height")}, reverse=True)

    m.resolve_video = resolve_video
    m.available_heights = available_heights
    m.height_label = lambda h: "%dp" % int(h)
    m.pick_progressive = lambda info, max_height=None: (None, None)
    m.encode_headers = lambda headers: "User-Agent=ua" if headers else ""
    m.original_audio_language = lambda info: None
    m.audio_languages = lambda info: []
    m.target_audio_language = (
        lambda mode, lang: None if mode == "auto" or not lang else lang)
    m.isa_audio_language = lambda lang: lang
    m.audio_language_supported = lambda info, lang: False
    m.playable_subtitle_urls = lambda info, lang=None: []
    return m


def _fake_ytlib():
    m = types.ModuleType("ytlib")

    def search(query, limit=20):
        state["searches"].append(query)
        return [{"id": VID1, "title": "Fake title", "description": "d",
                 "thumbnail": "", "duration": 300}]

    m.search = search
    m.search_channels = lambda query, limit=20: []
    m.channel_uploads = lambda channel_id, limit=50, offset=0: []
    return m


def _modules():
    m = types.ModuleType("xbmc")
    m.LOGINFO = 1
    m.LOGERROR = 4
    m.LOGDEBUG = 0
    m.translatePath = lambda p: p
    m.log = lambda msg, level=1: None
    m.Monitor = _Monitor
    if state["player"] is not None:
        m.Player = lambda: state["player"]

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
    plugin.setResolvedUrl = lambda handle, ok, item: state["resolved"].append((ok, item))
    plugin.setContent = lambda *a, **k: None

    return {"xbmc": m, "xbmcaddon": addon, "xbmcgui": gui,
            "xbmcplugin": plugin, "resolver": _fake_resolver(),
            "ytlib": _fake_ytlib()}


def run(action_url):
    """Run default.py like Kodi would for `action_url` (e.g. 'action=play&...')."""
    state["items"] = []
    state["ended"] = False
    state["notifications"] = []
    state["resolved"] = []
    state["asked"] = []
    state["selected"] = []
    state["searches"] = []
    sys.argv = ["plugin://%s/" % ADDON_ID, "1", "?" + action_url]
    for name, mod in _modules().items():
        sys.modules[name] = mod
    return runpy.run_path(ADDON_PATH + "/default.py", run_name="__main__")


# --- helpers ----------------------------------------------------------------

def query_of(url):
    return dict(urllib.parse.parse_qsl(url.split("?", 1)[1]))


def action_of(url):
    return query_of(url).get("action")


def read_history(data_dir):
    path = os.path.join(data_dir, "history.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as stream:
        return json.load(stream)


def watch_entries(data_dir):
    return read_history(data_dir).get("watch") or []


def find_entry(data_dir, video_id):
    for entry in watch_entries(data_dir):
        if entry["video_id"] == video_id:
            return entry
    return None


def no_wait(seconds):
    """A wait that does not sleep (keeps the monitor tests instant)."""
    return False


def play(video_id):
    """A plain play (as from a search result: no resume flag)."""
    return run("action=play&video_id=%s" % video_id)


def replay(video_id):
    """A replay from the Watch history section (resume flag set)."""
    return run("action=play&video_id=%s&resume=1" % video_id)


def main():
    profile = tempfile.mkdtemp(prefix="pipejoint-history-shim-")
    data_dir = os.path.join(profile, "addon_data")
    state["profile"] = data_dir
    try:
        # --- 2.1 recording on play ------------------------------------------
        print("=== 2.1 starting playback records the video ===")
        play(VID1)
        check("play resolved", state["resolved"] and state["resolved"][0][0] is True)
        entries = watch_entries(data_dir)
        check("one entry recorded", len(entries) == 1, repr(entries))
        check("entry carries the video id", entries and entries[0]["video_id"] == VID1,
              repr(entries))
        check("entry carries the display data",
              entries and entries[0]["title"] == "Fake title %s" % VID1
              and entries[0]["url"] == WATCH_URL % VID1
              and entries[0]["thumbnail"] == "https://t/thumb.png"
              and entries[0]["duration"] == 300.0, repr(entries))
        check("no position yet", entries and entries[0]["position"] is None,
              repr(entries))

        print("=== 2.1 rewatch updates the entry instead of duplicating ===")
        play(VID2)
        play(VID1)
        check("rewatch keeps one entry and moves it to the top",
              [e["video_id"] for e in watch_entries(data_dir)] == [VID1, VID2],
              repr([e["video_id"] for e in watch_entries(data_dir)]))

        print("=== 2.1 playback without a resolvable profile still plays ===")
        state["profile"] = None
        state["resolved"] = []
        play(VID3)
        check("play resolved without a store",
              state["resolved"] and state["resolved"][0][0] is True)
        state["profile"] = data_dir

        # --- 2.2 the monitor seam, driven by a scripted player ---------------
        print("=== 2.2 monitor_playback stores the stop position ===")
        db_dir = os.path.join(profile, "monitor")
        history = store.WatchHistoryStore(db_dir)
        history.record(VID1, "Fake title", duration=300)
        player = _FakePlayer([True, True, False], times=[123.4])
        position = player_monitor.monitor_playback(history, VID1, player,
                                                   wait=no_wait)
        check("position returned", position == 123.4, repr(position))
        check("position persisted", history.find(VID1)["position"] == 123.4,
              repr(history.find(VID1)))
        check("reopen sees the position",
              store.WatchHistoryStore(db_dir).find(VID1)["position"] == 123.4)

        print("=== 2.2 playback that ends without a position stays fact-only ===")
        history.record(VID2, "Fake title", duration=300)
        ended = _FakePlayer([True, False], time_error=True)
        check("nothing stored when the player reports no time",
              player_monitor.monitor_playback(history, VID2, ended, wait=no_wait) is None)
        check("entry kept without a resume point",
              history.find(VID2) is not None and history.find(VID2)["position"] is None,
              repr(history.find(VID2)))

        print("=== 2.2 a player that never starts does not hang ===")
        never = _FakePlayer([False] * 5)
        check("gives up after the start polls",
              player_monitor.monitor_playback(history, VID2, never, wait=no_wait,
                                             start_polls=3) is None)
        check("no extra time read after giving up", never.times == [], repr(never.times))

        print("=== 2.2 polls while the player plays, then stops ===")
        waits = []

        def counting_wait(seconds):
            waits.append(seconds)
            return False

        history.record(VID3, "Fake title", duration=300)
        # Script: playing (start check) -> playing -> playing -> stopped, so the
        # observe loop sleeps once per still-playing poll: two waits.
        polling = _FakePlayer([True, True, True, False], times=[50.0])
        player_monitor.monitor_playback(history, VID3, polling, wait=counting_wait)
        check("one wait per still-playing poll", len(waits) == 2, repr(waits))
        check("polled with the configured interval",
              waits and set(waits) == {player_monitor.POLL_SECONDS}, repr(waits))
        check("position stored after the polls",
              history.find(VID3)["position"] == 50.0, repr(history.find(VID3)))

        print("=== 2.2 no store -> no crash, nothing stored ===")
        idle = _FakePlayer([True, False], times=[10.0])
        check("without a store the position is not returned",
              player_monitor.monitor_playback(None, VID1, idle, wait=no_wait) is None)

        print("=== 2.2 the router observes the player after setResolvedUrl ===")
        state["player"] = _FakePlayer([True, False], times=[42.0])
        play(VID3)
        check("stop position reached the watch history",
              (find_entry(data_dir, VID3) or {}).get("position") == 42.0,
              repr(find_entry(data_dir, VID3)))
        state["player"] = None

        print("=== 2.2 without a player the router does not block ===")
        play(VID3)
        check("position untouched by a later play",
              (find_entry(data_dir, VID3) or {}).get("position") == 42.0,
              repr(find_entry(data_dir, VID3)))

        print("=== 2.2 no Kodi player available -> seam disabled ===")
        sys.modules.pop("xbmc", None)
        check("new_player() without xbmc is None",
              player_monitor.new_player() is None)
        # --- 3.1 resume flow --------------------------------------------------
        print("=== 3.1 a saved position offers to resume ===")
        state["select_return"] = 0          # "Resume from ..."
        replay(VID3)                        # positioned at 42s by the monitor
        check("resume prompt offered with both choices",
              state["selected"] and state["selected"][0][0] == "Resume playback"
              and state["selected"][0][1] == ["Resume from 0:42",
                                              "Start from the beginning"],
              repr(state["selected"]))
        check("accepted resume sets the start offset",
              state["resolved"] and
              state["resolved"][0][1].props.get("StartOffset") == "42",
              repr(state["resolved"][0][1].props if state["resolved"] else None))

        print("=== 3.1 declining the resume starts from the beginning ===")
        state["select_return"] = 1
        replay(VID3)
        check("no start offset when the resume is declined",
              state["resolved"]
              and "StartOffset" not in state["resolved"][0][1].props,
              repr(state["resolved"][0][1].props if state["resolved"] else None))

        print("=== 3.1 no position -> no prompt, no offset ===")
        state["select_return"] = 0
        replay(VID1)                        # VID1 was never stopped partway
        check("no prompt without a saved position", state["selected"] == [],
              repr(state["selected"]))
        check("no offset without a saved position",
              state["resolved"]
              and "StartOffset" not in state["resolved"][0][1].props)

        print("=== 3.1 a near-end position does not force a resume ===")
        db = replay(VID3)["get_watch_store"]()
        db.set_position(VID2, 295)          # duration is 300s
        state["select_return"] = 0
        replay(VID2)
        check("near-end position offers no resume prompt", state["selected"] == [],
              repr(state["selected"]))
        check("near-end position starts from the beginning",
              state["resolved"]
              and "StartOffset" not in state["resolved"][0][1].props)

        print("=== 3.1 a plain play never asks about resuming ===")
        state["select_return"] = 0
        play(VID3)                          # 42s saved, but not a history replay
        check("no prompt on a plain play", state["selected"] == [],
              repr(state["selected"]))
        check("no offset on a plain play",
              state["resolved"]
              and "StartOffset" not in state["resolved"][0][1].props)

        # --- 3.2 Watch history section ---------------------------------------
        print("=== 3.2 the Watch history section lists entries newest first ===")
        play(VID1)
        play(VID2)
        play(VID3)
        run("action=%s" % WATCH_HISTORY_ACTION)
        check("section closed its directory", state["ended"] is True)
        labels = [item.label for _, item, _ in state["items"]]
        check("entries are labelled with the stored titles",
              labels == ["Fake title %s" % VID3, "Fake title %s" % VID2,
                         "Fake title %s" % VID1], repr(labels))
        check("entries are playable rows (not folders)",
              all(folder is False for _, _, folder in state["items"]))
        targets = [query_of(url) for url, _, _ in state["items"]]
        check("newest first",
              [t.get("video_id") for t in targets] == [VID3, VID2, VID1],
              repr([t.get("video_id") for t in targets]))
        check("rows replay with the resume flag",
              all(t.get("action") == "play" and t.get("resume") == "1"
                  for t in targets), repr(targets))

        print("=== 3.2 the main menu reaches the Watch history section ===")
        globs = run("")
        menu = [(item.label, action_of(url)) for url, item, _ in state["items"]]
        check("menu lists Watch history between search and subscriptions",
              [label for label, _ in menu] == ["Search videos", "Search channels",
                                              "Watch history", "My subscriptions"],
              repr([label for label, _ in menu]))
        check("Watch history row targets the router action",
              menu[2][1] == WATCH_HISTORY_ACTION, repr(menu[2]))
        check("data_dir() still resolves for the menu", bool(globs["data_dir"]()))

        # --- 3.3 removing / clearing from the context menu --------------------
        print("=== 3.3 context menu removes one entry or clears everything ===")
        run("action=%s" % WATCH_HISTORY_ACTION)
        contexts = [dict(item.context_menu) for _, item, _ in state["items"]]
        check("every row offers a fresh start",
              all("Play from the beginning" in ctx for ctx in contexts),
              repr([sorted(ctx) for ctx in contexts]))
        check("every row offers remove + clear",
              all("Remove from watch history" in ctx and "Clear watch history" in ctx
                  for ctx in contexts), repr([sorted(ctx) for ctx in contexts]))
        remove_url = contexts[0]["Remove from watch history"]
        check("remove targets remove_history with the video id",
              query_of(remove_url).get("action") == "remove_history"
              and query_of(remove_url).get("video_id") == VID3, remove_url)
        fresh_url = contexts[0]["Play from the beginning"]
        check("fresh start targets a play without resume",
              query_of(fresh_url).get("action") == "play"
              and query_of(fresh_url).get("resume") == "0"
              and query_of(fresh_url).get("video_id") == VID3, fresh_url)

        run(remove_url.split("?", 1)[1])
        check("removed entry is gone", find_entry(data_dir, VID3) is None)
        check("other entries remain",
              [e["video_id"] for e in watch_entries(data_dir)] == [VID2, VID1],
              repr([e["video_id"] for e in watch_entries(data_dir)]))
        check("section reopened without the removed entry",
              [item.label for _, item, _ in state["items"]] ==
              ["Fake title %s" % VID2, "Fake title %s" % VID1],
              repr([item.label for _, item, _ in state["items"]]))

        clear_url = dict(state["items"][0][1].context_menu)["Clear watch history"]
        check("clear targets clear_history",
              query_of(clear_url).get("action") == "clear_history", clear_url)
        run(clear_url.split("?", 1)[1])
        check("history emptied", watch_entries(data_dir) == [],
              repr(watch_entries(data_dir)))
        check("empty section renders no rows", state["items"] == [],
              repr(state["items"]))
        check("empty section informs the user", bool(state["notifications"]),
              repr(state["notifications"]))
        check("empty section still closed the directory", state["ended"] is True)
    finally:
        shutil.rmtree(profile, ignore_errors=True)

    if failures:
        print("RESULT: FAIL (%d check(s): %s)" % (len(failures), ", ".join(failures)))
        sys.exit(1)
    print("RESULT: OK (watch recording + player-monitor seam)")


if __name__ == "__main__":
    main()

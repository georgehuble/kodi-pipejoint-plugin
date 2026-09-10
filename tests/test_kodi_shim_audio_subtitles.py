# -*- coding: utf-8 -*-
"""Deterministic Kodi-shim checks for the audio/subtitle default settings.

Runs default.py exactly as Kodi would, but with a fake resolver (no network),
a configurable Addon.getSetting, a ListItem that records properties and
attached subtitles, and a scripted fake player that drives the post-start audio
selection. Covers change tasks 2.2 (reading default_audio into (mode, lang) and
subtitles into a bool), 2.4 (ISA audio-language property + logging of the
target/available/selected track), 3.1 (multiaudio: Original starts on the
original language, an explicit tag on its language) and 3.2 (subtitles attached
only when On and playable tracks exist; Auto and a missing target switch
nothing). The multiaudio tracks mirror the real kodi.log case of the
fix-audio-language-code-match change: a two-letter `ru` original is reported by
the player as the three-letter `rus`, next to a leading `en-US` auto-dub.

Usage:  python3 tests/test_kodi_shim_audio_subtitles.py
"""

import os
import runpy
import sys
import types
import xml.etree.ElementTree as ET

ADDON_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB_PATH = os.path.join(ADDON_PATH, "resources", "lib")
sys.path.insert(0, LIB_PATH)

# Single source of truth: read the add-on id from the manifest (addon.xml).
ADDON_ID = ET.parse(os.path.join(ADDON_PATH, "addon.xml")).getroot().get("id")

# --- configurable fakes -----------------------------------------------------

settings = {
    "default_quality": "0",
    "default_audio": "Auto",
    "subtitles": "Off",
}
resolved = []  # list of (succeeded, listitem)
logs = []  # captured xbmc.log lines
PASSED = []

#: Scripted state of the fake xbmc.Player, driven by the monitor under test.
player_state = {
    "tracks": [],
    "selected": None,
    "switches": [],
    "unavailable": False,
    "switch_raises": False,
    "poll_limit": 3,
}

#: Player-side audio streams for the multiaudio scenario: original `rus` and dub
#: `en-US`, each in AAC-LC and HE-AAC. Mirrors the real kodi.log case where the
#: `ru` original is reported with the ISO 639-2/T code and the en-US dub leads.
MULTIAUDIO_TRACKS = [
    {"language": "rus", "name": "Russian original", "codec": "aac-lc"},
    {"language": "rus", "name": "Russian original", "codec": "he-aac"},
    {"language": "en-US", "name": "English dubbed", "codec": "aac-lc"},
    {"language": "en-US", "name": "English dubbed", "codec": "he-aac"},
]

HLS_URL = "https://cdn.example/master.m3u8"
PROGRESSIVE = "https://prog.example/video.mp4"
VTT_RU = "https://cdn.example/ru.vtt"
VTT_EN = "https://cdn.example/en.vtt"


class _Monitor(object):
    """Immediate-return xbmc.Monitor double so the monitor never really sleeps."""

    def waitForAbort(self, seconds):
        return False


class _Player(object):
    """Scripted xbmc.Player double driving the post-start audio selection."""

    def __init__(self):
        self._polls = 0

    def isPlaying(self):
        self._polls += 1
        return self._polls <= player_state["poll_limit"]

    def getTime(self):
        return 0.0

    def getAvailableAudioStreams(self):
        if player_state["unavailable"]:
            raise RuntimeError("no audio stream API")
        return player_state["tracks"]

    def setAudioStream(self, index):
        if player_state["switch_raises"]:
            raise RuntimeError("cannot switch")
        player_state["selected"] = index
        player_state["switches"].append(index)


def check(name, cond):
    if not cond:
        print("FAIL: %s" % name)
        sys.exit(1)
    PASSED.append(name)
    print("  ok: %s" % name)


def _info(with_subtitles=True):
    """Fake yt-dlp info: ru original audio + en auto + optional subtitle tracks."""
    formats = [
        {
            "protocol": "https",
            "acodec": "mp4a",
            "vcodec": "none",
            "language": "ru",
            "format_note": "Russian original (default)",
        },
        {
            "protocol": "https",
            "acodec": "mp4a",
            "vcodec": "none",
            "language": "en",
            "format_note": "dubbed-auto",
        },
        {
            "protocol": "https",
            "vcodec": "avc1",
            "acodec": "mp4a",
            "height": 720,
            "url": PROGRESSIVE,
        },
        {
            "protocol": "m3u8_native",
            "vcodec": "avc1",
            "acodec": "none",
            "height": 720,
            "url": HLS_URL,
            "manifest_url": HLS_URL,
            "http_headers": {"User-Agent": "ua"},
        },
    ]
    info = {
        "title": "Fake title",
        "description": "Fake desc",
        "duration": 300,
        "thumbnail": "",
        "formats": formats,
    }
    if with_subtitles:
        info["subtitles"] = {"ru": [{"url": VTT_RU, "ext": "vtt"}]}
        info["automatic_captions"] = {"en": [{"url": VTT_EN, "ext": "vtt"}]}
    return info


def _no_subtitle_info():
    """Resolved video without any subtitle/caption tracks."""
    info = _info(with_subtitles=False)
    info.pop("subtitles", None)
    info.pop("automatic_captions", None)
    return info


def _install_modules(kind="hls", info=None):
    """Install xbmc stubs and a real resolver with a stubbed resolve_video.

    The resolver's pure helpers are used for real; only the network call
    (resolve_video) is replaced so the router can run offline. The xbmc stub
    also exposes a scripted Player so the router's post-start audio selection
    runs, and an immediate-return Monitor so it never really sleeps.
    """
    import resolver as real_resolver  # pure, xbmc-free

    if info is None:
        info = _info()

    def resolve_video(video_id, allow_progressive=True, max_height=None):
        if kind == "hls":
            return "hls", HLS_URL, {"User-Agent": "ua"}, info
        return "progressive", PROGRESSIVE, {}, info

    real_resolver.resolve_video = resolve_video
    real_resolver.extract = None  # must not be reached on these paths

    class _InfoTag(object):
        def __init__(self):
            self.title = None
            self.plot = None
            self.duration = None

        def setTitle(self, v):
            self.title = v

        def setPlot(self, v):
            self.plot = v

        def setDuration(self, v):
            self.duration = v

    class _ListItem(object):
        def __init__(self, path=None, **kw):
            self.path = path
            self.props = {}
            self.art = {}
            self.tag = _InfoTag()
            self.subtitles = None
            self.content_lookup = None
            self.mime = None

        def setContentLookup(self, v):
            self.content_lookup = v

        def setMimeType(self, v):
            self.mime = v

        def setProperty(self, k, v):
            self.props[k] = v

        def setArt(self, d):
            self.art = d

        def getVideoInfoTag(self):
            return self.tag

        def setSubtitles(self, urls):
            self.subtitles = list(urls)

    class _Dialog(object):
        def notification(self, *a, **k):
            pass

    class _Addon(object):
        def getAddonInfo(self, key):
            return {"id": ADDON_ID, "name": "PipeJoint", "path": ADDON_PATH}[key]

        def getSetting(self, key):
            return settings.get(
                key, {"default_audio": "Auto", "subtitles": "Off", "default_quality": "0"}[key]
            )

    m = types.ModuleType("xbmc")
    m.LOGINFO = 1
    m.LOGERROR = 4
    m.log = lambda msg, level=1: logs.append(msg)
    m.Monitor = _Monitor
    m.Player = _Player

    a = types.ModuleType("xbmcaddon")
    a.Addon = _Addon

    g = types.ModuleType("xbmcgui")
    g.ListItem = _ListItem
    g.Dialog = _Dialog
    g.INPUT_ALPHANUM = 0
    g.NOTIFICATION_ERROR = "error"

    p = types.ModuleType("xbmcplugin")

    def setResolvedUrl(handle, succeeded, listitem):
        resolved.append((succeeded, listitem))

    p.setResolvedUrl = setResolvedUrl
    p.endOfDirectory = lambda *a, **k: None
    p.addDirectoryItem = lambda *a, **k: True
    p.setContent = lambda *a, **k: None

    sys.modules["xbmc"] = m
    sys.modules["xbmcaddon"] = a
    sys.modules["xbmcgui"] = g
    sys.modules["xbmcplugin"] = p
    sys.modules["resolver"] = real_resolver


def _reset():
    del resolved[:]
    del logs[:]
    settings["default_audio"] = "Auto"
    settings["subtitles"] = "Off"
    player_state["tracks"] = list(MULTIAUDIO_TRACKS)
    player_state["selected"] = None
    player_state["switches"] = []
    player_state["unavailable"] = False
    player_state["switch_raises"] = False
    player_state["poll_limit"] = 3


def _run(argv, run_name="__main__"):
    sys.argv = argv
    return runpy.run_path(ADDON_PATH + "/default.py", run_name=run_name)


# --- 2.2 reading ------------------------------------------------------------


def scenario_2_2_read_audio_preference():
    print("scenario 2.2: default_audio -> (mode, lang)")
    info = _info()
    _reset()

    # Auto -> auto mode, no language.
    settings["default_audio"] = "Auto"
    mod = _run(
        ["plugin://%s/" % ADDON_ID, "1", "?video_id=abc"], run_name="default_audio_subtitles"
    )
    check("2.2 Auto -> ('auto', None)", mod["audio_preference"](info) == ("auto", None))

    # Original -> resolved original language (ru, marked original).
    settings["default_audio"] = "Original"
    check("2.2 Original -> ('original', 'ru')", mod["audio_preference"](info) == ("original", "ru"))

    # Explicit tag -> language mode with that tag.
    settings["default_audio"] = "ru"
    check("2.2 'ru' -> ('language', 'ru')", mod["audio_preference"](info) == ("language", "ru"))
    settings["default_audio"] = "en-US"
    check(
        "2.2 'en-US' -> ('language', 'en-US')",
        mod["audio_preference"](info) == ("language", "en-US"),
    )

    # Original with no marked/no audio tracks -> original_audio_language None.
    no_audio = {
        "formats": [{"protocol": "https", "vcodec": "avc1", "acodec": "mp4a", "height": 720}]
    }
    settings["default_audio"] = "Original"
    check(
        "2.2 Original w/o audio -> lang None",
        mod["audio_preference"](no_audio) == ("original", None),
    )


def scenario_2_2_read_subtitles_default():
    print("scenario 2.2: subtitles -> bool")
    _reset()
    mod = _run(
        ["plugin://%s/" % ADDON_ID, "1", "?video_id=abc"], run_name="default_audio_subtitles"
    )
    settings["subtitles"] = "On"
    check("2.2 subtitles On -> True", mod["subtitles_default"]() is True)
    settings["subtitles"] = "Off"
    check("2.2 subtitles Off -> False", mod["subtitles_default"]() is False)
    # Missing key falls back to the settings.xml default Off.
    del settings["subtitles"]
    check("2.2 subtitles unset -> False", mod["subtitles_default"]() is False)
    settings["subtitles"] = "Off"


# --- 3.1 HLS audio-language property ----------------------------------------


def scenario_3_1_auto_no_property():
    print("scenario 3.1: Auto leaves no audio-language property")
    _install_modules(kind="hls")
    _reset()
    _run(["plugin://%s/" % ADDON_ID, "1", "?action=play&video_id=abc"])
    check("3.1 auto resolved ok", resolved and resolved[0][0] is True)
    item = resolved[0][1]
    prop = "inputstream.adaptive.original_audio_language"
    check("3.1 auto no audio-language property", prop not in item.props)
    check("3.1 auto no subtitles attached", item.subtitles is None)


def scenario_3_1_original_property():
    print("scenario 3.1: Original requests the original language")
    _install_modules(kind="hls")
    _reset()
    settings["default_audio"] = "Original"
    _run(["plugin://%s/" % ADDON_ID, "1", "?action=play&video_id=abc"])
    check("3.1 original resolved ok", resolved and resolved[0][0] is True)
    item = resolved[0][1]
    check(
        "3.1 original requests the manifest form 'rus'",
        item.props.get("inputstream.adaptive.original_audio_language") == "rus",
    )


def scenario_3_1_explicit_language_property():
    print("scenario 3.1: explicit available language requests it")
    _install_modules(kind="hls")
    _reset()
    settings["default_audio"] = "ru"
    _run(["plugin://%s/" % ADDON_ID, "1", "?action=play&video_id=abc"])
    item = resolved[0][1]
    check(
        "3.1 'ru' requests the manifest form 'rus'",
        item.props.get("inputstream.adaptive.original_audio_language") == "rus",
    )


def scenario_3_1_unavailable_language_falls_back():
    print("scenario 3.1: unavailable language leaves the player's choice")
    _install_modules(kind="hls")
    _reset()
    settings["default_audio"] = "de"  # not among the video's audio languages
    _run(["plugin://%s/" % ADDON_ID, "1", "?action=play&video_id=abc"])
    check("3.1 unavailable still plays", resolved and resolved[0][0] is True)
    item = resolved[0][1]
    prop = "inputstream.adaptive.original_audio_language"
    check("3.1 unavailable -> no audio-language property", prop not in item.props)
    check("3.1 unavailable -> nothing switched", player_state["selected"] is None)


def scenario_3_1_progressive_no_property():
    print("scenario 3.1: progressive stream sets no audio-language property")
    _install_modules(kind="progressive")
    _reset()
    settings["default_audio"] = "Original"
    _run(["plugin://%s/" % ADDON_ID, "1", "?action=play&video_id=abc"])
    check("3.1 progressive resolved ok", resolved and resolved[0][0] is True)
    item = resolved[0][1]
    prop = "inputstream.adaptive.original_audio_language"
    check("3.1 progressive no audio-language property", prop not in item.props)
    check("3.1 progressive nothing switched", player_state["selected"] is None)


# --- 3.1 multiaudio: deterministic post-start selection ---------------------


def scenario_3_1_multiaudio_original():
    print("scenario 3.1: multiaudio Original starts on the original language")
    _install_modules(kind="hls")
    _reset()
    settings["default_audio"] = "Original"
    _run(["plugin://%s/" % ADDON_ID, "1", "?action=play&video_id=abc"])
    item = resolved[0][1]
    check("3.1 multiaudio original resolved ok", resolved and resolved[0][0] is True)
    check(
        "3.1 multiaudio original requests the manifest form 'rus' via ISA",
        item.props.get("inputstream.adaptive.original_audio_language") == "rus",
    )
    check(
        "3.1 multiaudio original switched to a rus rendition (0 or 1)",
        player_state["selected"] in (0, 1),
    )
    check("3.1 multiaudio original switched exactly once", player_state["switches"] == [0])
    check(
        "3.1 multiaudio logs the requested language",
        any("audio_target=ru" in line for line in logs),
    )
    check("3.1 multiaudio logs the switched track", any("switched audio" in line for line in logs))


def scenario_3_1_multiaudio_explicit():
    print("scenario 3.1: multiaudio explicit en-US starts on English")
    _install_modules(kind="hls")
    _reset()
    settings["default_audio"] = "en-US"
    _run(["plugin://%s/" % ADDON_ID, "1", "?action=play&video_id=abc"])
    check("3.1 multiaudio explicit resolved ok", resolved and resolved[0][0] is True)
    check(
        "3.1 multiaudio explicit switched to an en-US AAC-LC track (index 2)",
        player_state["selected"] == 2,
    )


def scenario_3_2_player_monitor_code_match():
    print("scenario 3.2: player monitor selects a three-letter track / misses safely")
    _install_modules(kind="hls")
    _reset()
    import player_monitor

    player_state["tracks"] = list(MULTIAUDIO_TRACKS)
    index = player_monitor.select_audio_track(_Player(), "ru", log=logs.append)
    check("3.2 select_audio_track picks a rus rendition (0 or 1)", index in (0, 1))
    check("3.2 select_audio_track switched to that rendition", player_state["selected"] == index)

    player_state["selected"] = None
    del player_state["switches"][:]
    miss = player_monitor.select_audio_track(_Player(), "de", log=logs.append)
    check("3.2 select_audio_track miss returns None", miss is None)
    check("3.2 select_audio_track miss switches nothing", player_state["switches"] == [])
    check("3.2 select_audio_track miss is logged", any("no audio track" in line for line in logs))


# --- 2.3 fallback / idempotency ---------------------------------------------


def scenario_2_3_api_unavailable():
    print("scenario 2.3: unavailable stream API never breaks playback")
    _install_modules(kind="hls")
    _reset()
    player_state["unavailable"] = True
    settings["default_audio"] = "Original"
    _run(["plugin://%s/" % ADDON_ID, "1", "?action=play&video_id=abc"])
    check("2.3 unavailable API resolved ok", resolved and resolved[0][0] is True)
    check("2.3 unavailable API switched nothing", player_state["switches"] == [])
    check("2.3 unavailable API logged the miss", any("no audio track" in line for line in logs))


def scenario_2_3_switch_failure():
    print("scenario 2.3: a failing switch never breaks playback")
    _install_modules(kind="hls")
    _reset()
    player_state["switch_raises"] = True
    settings["default_audio"] = "Original"
    _run(["plugin://%s/" % ADDON_ID, "1", "?action=play&video_id=abc"])
    check("2.3 failing switch resolved ok", resolved and resolved[0][0] is True)
    check("2.3 failing switch selected nothing", player_state["selected"] is None)
    check("2.3 failing switch logged the failure", any("could not switch" in line for line in logs))


# --- 3.2 subtitle attachment ------------------------------------------------


def scenario_3_2_on_attaches():
    print("scenario 3.2: subtitles On attaches playable urls")
    _install_modules(kind="hls")
    _reset()
    settings["subtitles"] = "On"
    _run(["plugin://%s/" % ADDON_ID, "1", "?action=play&video_id=abc"])
    check("3.2 on resolved ok", resolved and resolved[0][0] is True)
    item = resolved[0][1]
    check(
        "3.2 on attached vtt urls (ru first)",
        item.subtitles is not None and VTT_RU in item.subtitles,
    )


def scenario_3_2_off_attaches_nothing():
    print("scenario 3.2: subtitles Off attaches nothing")
    _install_modules(kind="hls")
    _reset()
    settings["subtitles"] = "Off"
    _run(["plugin://%s/" % ADDON_ID, "1", "?action=play&video_id=abc"])
    item = resolved[0][1]
    check("3.2 off no subtitles attached", item.subtitles is None)


def scenario_3_2_no_tracks_attaches_nothing():
    print("scenario 3.2: no subtitle tracks -> nothing attached even when On")
    _install_modules(kind="hls", info=_no_subtitle_info())
    _reset()
    settings["subtitles"] = "On"
    _run(["plugin://%s/" % ADDON_ID, "1", "?action=play&video_id=abc"])
    check("3.2 no tracks resolved ok", resolved and resolved[0][0] is True)
    item = resolved[0][1]
    check("3.2 no tracks nothing attached", item.subtitles is None)


def scenario_3_2_progressive_attaches():
    print("scenario 3.2: subtitles attach on progressive too")
    _install_modules(kind="progressive")
    _reset()
    settings["subtitles"] = "On"
    _run(["plugin://%s/" % ADDON_ID, "1", "?action=play&video_id=abc"])
    check("3.2 progressive on resolved ok", resolved and resolved[0][0] is True)
    item = resolved[0][1]
    check(
        "3.2 progressive on attached urls", item.subtitles is not None and VTT_RU in item.subtitles
    )


def scenario_3_2_auto_no_switch():
    print("scenario 3.2: Auto switches nothing")
    _install_modules(kind="hls")
    _reset()
    settings["default_audio"] = "Auto"
    _run(["plugin://%s/" % ADDON_ID, "1", "?action=play&video_id=abc"])
    check("3.2 auto resolved ok", resolved and resolved[0][0] is True)
    check("3.2 auto switched nothing", player_state["switches"] == [])
    check("3.2 auto selected nothing", player_state["selected"] is None)


def scenario_3_2_missing_target():
    print("scenario 3.2: missing target language keeps the player's choice")
    _install_modules(kind="hls")
    _reset()
    settings["default_audio"] = "de"
    _run(["plugin://%s/" % ADDON_ID, "1", "?action=play&video_id=abc"])
    check("3.2 missing target resolved ok", resolved and resolved[0][0] is True)
    check("3.2 missing target switched nothing", player_state["switches"] == [])
    check("3.2 missing target logged the miss", any("no audio track" in line for line in logs))


def main():
    print("=== shim: audio/subtitle defaults ===")
    _install_modules(kind="hls")
    scenario_2_2_read_audio_preference()
    scenario_2_2_read_subtitles_default()
    scenario_3_1_auto_no_property()
    scenario_3_1_original_property()
    scenario_3_1_explicit_language_property()
    scenario_3_1_unavailable_language_falls_back()
    scenario_3_1_progressive_no_property()
    scenario_3_1_multiaudio_original()
    scenario_3_1_multiaudio_explicit()
    scenario_3_2_player_monitor_code_match()
    scenario_2_3_api_unavailable()
    scenario_2_3_switch_failure()
    scenario_3_2_on_attaches()
    scenario_3_2_off_attaches_nothing()
    scenario_3_2_no_tracks_attaches_nothing()
    scenario_3_2_progressive_attaches()
    scenario_3_2_auto_no_switch()
    scenario_3_2_missing_target()
    print("RESULT: OK (%d checks)" % len(PASSED))


if __name__ == "__main__":
    main()

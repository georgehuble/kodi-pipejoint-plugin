# -*- coding: utf-8 -*-
"""Shared Kodi shim for the router tests.

The router ([`default.py`](../default.py)) is written for Kodi: it imports the
`xbmc*` modules, reads add-on settings and hands a ListItem to the player. The
shim tests run it unchanged on a bare desktop by installing fake modules into
`sys.modules` first.

Everything the shim tests used to copy - the `xbmc` stubs, the add-on double,
the recording plugin calls and the fake `resolver`/`ytlib` - lives here once, so
a test only declares what it actually cares about.

The fake resolver deliberately *delegates* every pure helper to the real
[`resolver`](../resources/lib/resolver.py) module and only fakes `resolve_video`
(no network), so the helpers under test stay the production ones.
"""

import os
import runpy
import sys
import types
import xml.etree.ElementTree as ET

ADDON_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Single source of truth: read the add-on id from the manifest (addon.xml).
ADDON_ID = ET.parse(os.path.join(ADDON_PATH, "addon.xml")).getroot().get("id")

_LIB = os.path.join(ADDON_PATH, "resources", "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

# The real resolver: imported before any fake is installed into sys.modules, so
# its pure helpers can be delegated to instead of re-implemented per test.
import resolver as _real_resolver  # noqa: E402

HLS_URL = "https://cdn.example/master.m3u8"
PROGRESSIVE_URL = "https://cdn.example/progressive.mp4"

#: Settings every shim test starts from; tests override what they care about.
DEFAULT_SETTINGS = {
    "default_quality": "0",
    "show_higher_resolutions": "Off",
    "default_audio": "Auto",
    "subtitles": "Off",
}

#: Pure resolver helpers the fake module mirrors from the real resolver.
_DELEGATED = (
    "HLS_MIME",
    "available_heights",
    "height_label",
    "selectable_heights",
    "isa_resolution_label",
    "bandwidth_for_height",
    "pick_hls",
    "pick_progressive",
    "encode_headers",
    "audio_languages",
    "audio_language_supported",
    "original_audio_language",
    "target_audio_language",
    "isa_audio_language",
    "pick_audio_track",
    "subtitle_languages",
    "subtitle_url",
    "playable_subtitle_urls",
)


class Reporter:
    """Tiny check runner: abort on the first failure, print a summary at the end."""

    def __init__(self, title):
        self.title = title
        self.checks = 0
        print("=== %s ===" % title)

    def check(self, name, condition):
        if not condition:
            print("FAIL: %s" % name)
            sys.exit(1)
        self.checks += 1
        print("  ok: %s" % name)

    def done(self):
        print("RESULT: OK (%d checks)" % self.checks)


class InfoTag:
    """Minimal `xbmcgui.ListItem.getVideoInfoTag()` double."""

    def __init__(self):
        self.title = None
        self.plot = None
        self.duration = 0
        self.cast = []

    def setTitle(self, value):
        self.title = value

    def setPlot(self, value):
        self.plot = value

    def setDuration(self, value):
        self.duration = value

    def setCast(self, value):
        self.cast = list(value)


class ListItem:
    """Minimal `xbmcgui.ListItem` double recording everything the router sets."""

    def __init__(self, label=None, path=None, **kwargs):
        self.label = label
        self.path = path
        self.props = {}
        self.art = {}
        self.context_menu = []
        self.subtitles = []
        self.mime = None
        self.content_lookup = None
        self.tag = InfoTag()

    def setProperty(self, key, value):
        self.props[key] = value

    def setArt(self, art):
        self.art = art

    def getVideoInfoTag(self):
        return self.tag

    def addContextMenuItems(self, items, replaceItems=False):
        self.context_menu = list(items)

    def setSubtitles(self, urls):
        self.subtitles = list(urls)

    def setMimeType(self, value):
        self.mime = value

    def setContentLookup(self, value):
        self.content_lookup = value

    def setPath(self, path):
        self.path = path


class Dialog:
    """Minimal `xbmcgui.Dialog` double backed by the harness' recorded state."""

    def __init__(self, harness):
        self._harness = harness

    def notification(self, *args, **kwargs):
        self._harness.notifications.append((args, kwargs))

    def select(self, heading, options):
        self._harness.dialog_calls.append((heading, list(options)))
        return self._harness.dialog_selection

    def input(self, heading, **kwargs):
        return self._harness.dialog_input

    def ok(self, heading, message=""):
        return True


class _Addon:
    """`xbmcaddon.Addon` double: settings come from the harness."""

    def __init__(self, harness):
        self._harness = harness

    def getAddonInfo(self, key):
        return {"id": ADDON_ID, "name": "PipeJoint", "path": ADDON_PATH}.get(key)

    def getSetting(self, key):
        return self._harness.settings.get(key, "")


def stub_ytlib(**overrides):
    """A no-network `ytlib` double.

    Pass `search=`, `search_channels=` or `channel_uploads=` to override the
    default (empty) results.
    """
    module = types.ModuleType("ytlib")
    module.search = overrides.get("search", lambda query, limit=20: [])
    module.search_channels = overrides.get("search_channels", lambda query, limit=20: [])
    module.channel_uploads = overrides.get(
        "channel_uploads", lambda channel_id, limit=50, offset=0: [])
    return module


class FakeResolver:
    """Drop-in `resolver` module with a canned, offline `resolve_video`.

    `heights` is the resolution ladder the fake video exposes, `kind` selects
    the HLS or progressive path, and `rates` maps a height to its video bitrate
    in kbit/s (used by the bandwidth-ceiling fallback).
    """

    def __init__(self, heights=(144, 240, 360, 480, 720, 1080), kind="hls",
                 rates=None):
        self.heights = list(heights)
        self.kind = kind
        self.rates = dict(rates or {})
        self.calls = []

    def info(self):
        """A yt-dlp-style info dict exposing the ladder as muxed + HLS formats."""
        formats = [
            {
                "protocol": "https",
                "vcodec": "avc1",
                "acodec": "mp4a",
                "height": height,
                "url": "https://prog.example/%dp.mp4" % height,
                "vbr": self.rates.get(height) or None,
            }
            for height in self.heights
        ]
        formats.append({
            "protocol": "m3u8_native",
            "vcodec": "avc1",
            "acodec": "none",
            "height": max(self.heights),
            "url": HLS_URL,
            "manifest_url": HLS_URL,
            "http_headers": {"User-Agent": "ua"},
        })
        return {
            "title": "Fake title",
            "description": "Fake desc",
            "duration": 300,
            "thumbnail": "",
            "formats": formats,
        }

    def resolve_video(self, video_id, allow_progressive=True, max_height=None):
        self.calls.append((video_id, max_height))
        info = self.info()
        if self.kind == "hls":
            return "hls", HLS_URL, {"User-Agent": "ua"}, info
        stream, headers = _real_resolver.pick_progressive(info, max_height=max_height)
        return "progressive", stream or PROGRESSIVE_URL, headers or {}, info

    def module(self):
        """The fake module to install as `sys.modules['resolver']`."""
        module = types.ModuleType("resolver")
        for name in _DELEGATED:
            setattr(module, name, getattr(_real_resolver, name))
        module.resolve_video = self.resolve_video
        return module


class Harness:
    """Fake Kodi environment for one or more router invocations."""

    def __init__(self):
        self.settings = dict(DEFAULT_SETTINGS)
        self.directory = []          # (url, item, is_folder) per addDirectoryItem
        self.resolved = []           # (succeeded, item) per setResolvedUrl
        self.dialog_calls = []       # (heading, options) per Dialog.select
        self.notifications = []      # (args, kwargs) per Dialog.notification
        self.dialog_selection = -1
        self.dialog_input = ""
        self.ended = False
        self.resolver = FakeResolver()
        self.ytlib = stub_ytlib()

    # -- assertions helpers --------------------------------------------------

    def item(self):
        """The ListItem last handed to `setResolvedUrl`."""
        return self.resolved[-1][1]

    # -- plumbing ------------------------------------------------------------

    def install(self):
        """Install the fake Kodi modules (and fakes under test) into sys.modules."""
        harness = self

        xbmc = types.ModuleType("xbmc")
        xbmc.LOGINFO = 1
        xbmc.LOGERROR = 4
        xbmc.LOGDEBUG = 0
        xbmc.translatePath = lambda path: path
        xbmc.log = lambda message, level=1: None

        xbmcaddon = types.ModuleType("xbmcaddon")
        xbmcaddon.Addon = lambda: _Addon(harness)

        xbmcgui = types.ModuleType("xbmcgui")
        xbmcgui.ListItem = ListItem
        xbmcgui.Dialog = lambda: Dialog(harness)
        xbmcgui.INPUT_ALPHANUM = 0
        xbmcgui.NOTIFICATION_ERROR = "error"
        xbmcgui.NOTIFICATION_WARNING = "warning"

        xbmcplugin = types.ModuleType("xbmcplugin")
        xbmcplugin.addDirectoryItem = (
            lambda handle, url, item, isFolder=False:
            harness.directory.append((url, item, isFolder)) or True)
        xbmcplugin.endOfDirectory = lambda handle: setattr(harness, "ended", True)
        xbmcplugin.setResolvedUrl = (
            lambda handle, succeeded, item: harness.resolved.append((succeeded, item)))
        xbmcplugin.setContent = lambda *args, **kwargs: None

        sys.modules["xbmc"] = xbmc
        sys.modules["xbmcaddon"] = xbmcaddon
        sys.modules["xbmcgui"] = xbmcgui
        sys.modules["xbmcplugin"] = xbmcplugin
        sys.modules["resolver"] = self.resolver.module()
        sys.modules["ytlib"] = self.ytlib

    def run(self, query=""):
        """Run default.py once, exactly as Kodi would invoke the plugin."""
        self.install()
        sys.argv = ["plugin://%s/" % ADDON_ID, "1", query]
        runpy.run_path(os.path.join(ADDON_PATH, "default.py"), run_name="__main__")

# -*- coding: utf-8 -*-
"""Kodi-shim test: run default.py exactly as Kodi would, with stubbed xbmc modules.

Verifies the plugin resolves a video and hands InputStream Adaptive an HLS
manifest via setResolvedUrl(succeeded=True).
"""

import os
import runpy
import sys
import types
import xml.etree.ElementTree as ET

# Repo root = one level above tests/
ADDON_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Single source of truth: read the add-on id from the manifest (addon.xml).
ADDON_ID = ET.parse(os.path.join(ADDON_PATH, "addon.xml")).getroot().get("id")

captured = {}


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


class _Dialog(object):
    def notification(self, *a, **k):
        print("  [dialog] notification:", a, k.get("icon") or k.get("title"))


class _Addon(object):
    def getAddonInfo(self, key):
        return {"id": ADDON_ID, "name": "YouTube Proto", "path": ADDON_PATH}[key]


def _make_xbmc():
    m = types.ModuleType("xbmc")
    m.LOGINFO = 1
    m.LOGERROR = 4
    m.translatePath = lambda p: p
    m.log = lambda msg, level=1: print("  [xbmc.log]", str(msg)[:160])
    return m


def _make_xbmcaddon():
    m = types.ModuleType("xbmcaddon")
    m.Addon = _Addon
    return m


def _make_xbmcgui():
    m = types.ModuleType("xbmcgui")
    m.ListItem = _ListItem
    m.Dialog = _Dialog
    m.NOTIFICATION_ERROR = "error"
    m.INPUT_ALPHANUM = 0
    return m


def _make_xbmcplugin():
    m = types.ModuleType("xbmcplugin")

    def setResolvedUrl(handle, succeeded, listitem):
        captured["succeeded"] = succeeded
        captured["handle"] = handle
        captured["listitem"] = listitem

    m.setResolvedUrl = setResolvedUrl
    m.setContent = lambda *a, **k: None
    m.endOfDirectory = lambda *a, **k: None
    m.addDirectoryItem = lambda *a, **k: True
    return m


def main():
    video_id = sys.argv[1] if len(sys.argv) > 1 else "1l2_uCyBXQ0"
    sys.argv = ["plugin://%s/" % ADDON_ID, "1", "?video_id=%s" % video_id]

    sys.modules["xbmc"] = _make_xbmc()
    sys.modules["xbmcaddon"] = _make_xbmcaddon()
    sys.modules["xbmcgui"] = _make_xbmcgui()
    sys.modules["xbmcplugin"] = _make_xbmcplugin()

    print("=== running default.py with video_id=%s ===" % video_id)
    runpy.run_path(ADDON_PATH + "/default.py", run_name="__main__")

    if not captured.get("succeeded"):
        print("RESULT: FAIL (not resolved)")
        sys.exit(1)

    item = captured["listitem"]
    print("RESULT: OK")
    print("  title      :", item.tag.title)
    print("  path       :", (item.path or "")[:100])
    print("  mime       :", item.mime)
    print("  inputstream:", item.props.get("inputstream"))
    print("  manifest_headers set:", bool(item.props.get("inputstream.adaptive.manifest_headers")))


if __name__ == "__main__":
    main()

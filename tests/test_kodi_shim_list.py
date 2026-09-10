# -*- coding: utf-8 -*-
"""Kodi-shim: render a 'results' directory page as Kodi would, offline.

`ytlib` is stubbed (see [`kodi_shim.py`](kodi_shim.py)) so no network is needed.
Verifies that every playable video item carries the "Play with quality..."
context-menu entry pointing at the play_quality action with the right video_id.

Usage:  python3 tests/test_kodi_shim_list.py
"""

import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kodi_shim import ADDON_ID, Harness, Reporter, stub_ytlib  # noqa: E402

FAKE_VIDEOS = [
    {"id": "aaa111", "title": "Fake video one", "description": "d1",
     "thumbnail": "", "duration": 120},
    {"id": "bbb222", "title": "Fake video two", "description": "d2",
     "thumbnail": "", "duration": 60},
]


def main():
    r = Reporter("shim: results page -> Play with quality context entry")

    h = Harness()
    h.ytlib = stub_ytlib(search=lambda query: list(FAKE_VIDEOS))
    h.run("?action=results&q=%s" % urllib.parse.quote_plus("kodi"))

    r.check("directory rendered and ended", bool(h.directory) and h.ended)
    playable = [entry for entry in h.directory if not entry[2]]
    r.check("two playable video items", len(playable) == 2)

    for _url, item, _is_folder in playable:
        ctx = dict(item.context_menu)
        label = next((key for key in ctx if "Play with quality" in key), None)
        r.check("item %r has the quality context entry" % item.label,
                label is not None)
        target = ctx[label]
        r.check("context url is a plugin url for %r" % item.label,
                target.startswith("plugin://%s/?" % ADDON_ID))
        query = dict(urllib.parse.parse_qsl(target.split("?", 1)[1]))
        r.check("context url targets play_quality for %r" % item.label,
                query.get("action") == "play_quality" and bool(query.get("video_id")))

    r.done()


if __name__ == "__main__":
    main()

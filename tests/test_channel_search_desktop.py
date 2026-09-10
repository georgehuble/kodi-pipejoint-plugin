# -*- coding: utf-8 -*-
"""Desktop check for ytlib.search_channels (no Kodi, offline by default).

The bundled YoutubeDL is stubbed so the channel-only filtering and sanitizing
are checked deterministically. Pass --live to additionally run one real query
against YouTube (the mechanism recorded in the change design D4).

Usage:  python3 tests/test_channel_search_desktop.py [--live] [query]
"""

import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "lib"))

import ytlib  # noqa: E402

CHANNEL_FILTER = "EgIQAg%253D%253D"

THUMBS = [{"url": "https://i.ytimg.com/vi/aaa/hqdefault.jpg", "width": 480},
          {"url": "https://yt3.googleusercontent.com/chan.png", "width": 900}]

#: A flat channel-search result: channels, plus entries that must be rejected.
ENTRIES = [
    {"_type": "url", "id": "UCchan0001", "channel_id": "UCchan0001",
     "title": "Fake Channel One",
     "channel_url": "https://www.youtube.com/channel/UCchan0001",
     "url": "https://www.youtube.com/channel/UCchan0001",
     "ie_key": "YoutubeTab", "thumbnails": THUMBS},
    {"_type": "url", "id": "UCchan0002", "channel_id": "UCchan0002",
     "title": "Fake Channel Two", "uploader": "Fake Channel Two",
     "url": "https://www.youtube.com/channel/UCchan0002",
     "ie_key": "YoutubeTab", "thumbnails": THUMBS},
    {"_type": "url", "id": "vic0000001", "title": "A video, not a channel",
     "webpage_url": "https://www.youtube.com/watch?v=vic0000001",
     "ie_key": "Youtube", "thumbnails": THUMBS},
    {"_type": "url", "id": "UCplaylist1", "title": "A playlist with a UC-ish id",
     "url": "https://www.youtube.com/playlist?list=PLabcdef123",
     "ie_key": "YoutubePlaylist", "thumbnails": THUMBS},
    {"_type": "url", "id": "UCnoname1", "channel_id": "UCnoname1",
     "url": "https://www.youtube.com/channel/UCnoname1", "ie_key": "YoutubeTab"},
    None,
]

#: A flat /videos-tab result: videos, and (as YouTube really returns them) no
#: channel_id on the entries. The first entry is a tab/section row - its `id` is
#: the channel id, which must never end up as a playable video.
VIDEO_ENTRIES = [
    {"_type": "url", "id": "UCchan0001", "channel_id": "UCchan0001",
     "title": "Fake Channel One - Videos",
     "url": "https://www.youtube.com/channel/UCchan0001/videos",
     "ie_key": "YoutubeTab", "thumbnails": THUMBS},
    {"_type": "url", "id": "flat0000001", "title": "Flat video one",
     "url": "https://www.youtube.com/watch?v=flat0000001", "ie_key": "Youtube",
     "duration": "61", "view_count": "1200", "thumbnails": THUMBS},
    {"_type": "url", "id": "flat0000002", "title": "Flat video two",
     "url": "https://www.youtube.com/watch?v=flat0000002", "ie_key": "Youtube",
     "duration": "2656", "view_count": "3000", "thumbnails": THUMBS},
    {"_type": "url", "id": "flat0000003", "title": "Flat video three",
     "url": "https://www.youtube.com/watch?v=flat0000003", "ie_key": "Youtube",
     "duration": "88", "view_count": "7500", "thumbnails": THUMBS},
]

failures = []


def check(name, ok, detail=""):
    print("  [%s] %s%s" % ("OK" if ok else "FAIL", name,
                           (" - %s" % detail) if detail else ""))
    if not ok:
        failures.append(name)


class _FakeYDL(object):
    urls = []
    opts = {}

    def __init__(self, opts):
        self.opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, url, download=False):
        _FakeYDL.urls.append(url)
        _FakeYDL.opts = self.opts
        entries = VIDEO_ENTRIES if "/videos" in url else ENTRIES
        return {"_type": "playlist", "entries": list(entries)}


class _BrokenYDL(object):
    def __init__(self, opts):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, url, download=False):
        raise RuntimeError("network down")


def main():
    live = "--live" in sys.argv[1:]
    query = next((a for a in sys.argv[1:] if not a.startswith("--")), "kurzgesagt")

    print("=== search_channels(%r) with a stubbed yt-dlp ===" % query)
    _FakeYDL.urls = []
    ytlib.YoutubeDL = _FakeYDL
    try:
        results = ytlib.search_channels(query, limit=10)
        print("  channels:", [r["channel_id"] for r in results])
        check("only channel entries returned",
              [r["channel_id"] for r in results] == ["UCchan0001", "UCchan0002"],
              repr(results))
        check("channel_id exposed",
              all(r["channel_id"].startswith("UC") for r in results))
        check("name exposed",
              [r["name"] for r in results] == ["Fake Channel One", "Fake Channel Two"],
              repr([r["name"] for r in results]))
        check("channel url exposed",
              results[0]["url"] == "https://www.youtube.com/channel/UCchan0001")
        check("thumbnail exposed", bool(results[0]["thumbnail"]),
              repr(results[0]["thumbnail"]))
        check("no extra keys leak into the result",
              all(set(r) == {"channel_id", "name", "url", "thumbnail"} for r in results),
              repr(sorted(results[0])))

        url = _FakeYDL.urls[0]
        check("search uses the channel-only filter",
              "sp=%s" % CHANNEL_FILTER in url, url)
        check("search url carries the query",
              "search_query=%s" % query.replace(" ", "+") in url, url)

        check("limit is honoured", len(ytlib.search_channels(query, limit=1)) == 1)
        check("the extractor is capped at the requested limit",
              _FakeYDL.opts.get("playlistend") == 1, repr(_FakeYDL.opts))

        print("=== channel_uploads stays bounded on big channels ===")
        _FakeYDL.urls = []
        uploads = ytlib.channel_uploads("UCchan0001", limit=2)
        url = _FakeYDL.urls[0]
        check("uses the channel's /videos tab",
              url.endswith("/channel/UCchan0001/videos"), url)
        check("the extractor fetches only the requested window",
              _FakeYDL.opts.get("playlist_items") == "1-2", repr(_FakeYDL.opts))
        check("does not resolve nested tab playlists",
              _FakeYDL.opts.get("extract_flat") is True, repr(_FakeYDL.opts))
        check("flat videos are kept and capped",
              [u["id"] for u in uploads] == ["flat0000001", "flat0000002"],
              repr([u["id"] for u in uploads]))
        check("tab/section entries never become videos",
              "UCchan0001" not in [u["id"] for u in uploads],
              repr([u["id"] for u in uploads]))
        check("the channel id is filled in for flat entries",
              all(u["channel_id"] == "UCchan0001" for u in uploads),
              repr([u["channel_id"] for u in uploads]))
        check("flat videos carry the fields the UI needs",
              uploads[0]["title"] == "Flat video one" and bool(uploads[0]["thumbnail"]),
              repr(uploads[0]))

        ytlib.channel_uploads("UCchan0001", limit=3, offset=9)
        check("a later page asks for its own window",
              _FakeYDL.opts.get("playlist_items") == "10-12", repr(_FakeYDL.opts))
    finally:
        ytlib.YoutubeDL = _FakeYDL

    print("=== a failing extractor yields no channels ===")
    ytlib.YoutubeDL = _BrokenYDL
    try:
        check("failure -> []", ytlib.search_channels(query) == [])
    finally:
        ytlib.YoutubeDL = _FakeYDL

    if live:
        import yt_dlp  # noqa: F401  (only imported for the live run)
        ytlib.YoutubeDL = yt_dlp.YoutubeDL
        print("=== LIVE search_channels(%r, limit=8) ===" % query)
        live_results = ytlib.search_channels(query, limit=8)
        print("  channels:", len(live_results))
        for r in live_results:
            print("  -", r["channel_id"], "|", (r["name"] or "")[:50],
                  "| thumb:", bool(r["thumbnail"]))
        check("live search returned channels", bool(live_results))
        check("live results carry a channel id and name",
              all(r["channel_id"].startswith("UC") and r["name"] for r in live_results))

    if failures:
        print("RESULT: FAIL (%d check(s): %s)" % (len(failures), ", ".join(failures)))
        sys.exit(1)
    print("RESULT: OK (search_channels keeps channels only, offline and%s)" %
          (" live" if live else " deterministic"))


if __name__ == "__main__":
    main()

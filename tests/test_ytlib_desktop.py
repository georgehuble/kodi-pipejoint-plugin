# -*- coding: utf-8 -*-
"""Desktop check for the catalog (ytlib) without Kodi."""

import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "lib"))

import ytlib  # noqa: E402


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "kodi addon"
    print("=== search(%r, limit=8) ===" % query)
    res = ytlib.search(query, limit=8)
    print("results:", len(res))
    for r in res[:8]:
        print("  -", r.get("id"), "|", (r.get("title") or "")[:50],
              "|", r.get("uploader"), "| thumb:", bool(r.get("thumbnail")),
              "| dur:", r.get("duration"))

    if len(sys.argv) > 2:
        cid = sys.argv[2]
        print("=== channel_uploads(%s, limit=5) ===" % cid)
        ups = ytlib.channel_uploads(cid, limit=5)
        print("uploads:", len(ups))
        for u in ups[:5]:
            print("  -", u.get("id"), "|", (u.get("title") or "")[:50], "|", u.get("channel_id"))


if __name__ == "__main__":
    main()

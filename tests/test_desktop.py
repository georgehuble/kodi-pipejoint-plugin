# -*- coding: utf-8 -*-
"""Desktop check for resolver.py (no Kodi required).

Usage:  python3 test_desktop.py [video_id ...]
"""

import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "lib"))

import resolver  # noqa: E402

DEFAULT_IDS = ["1l2_uCyBXQ0", "aqz-KE-bpKQ"]


def main():
    ids = sys.argv[1:] or DEFAULT_IDS
    for video_id in ids:
        print("=" * 70)
        print("video:", video_id)
        try:
            kind, stream, headers, info = resolver.resolve_video(video_id)
        except Exception as error:  # noqa: BLE001
            print("  FAILED:", error)
            continue
        host = stream.split("//")[1].split("/")[0]
        print("  title    :", info.get("title"))
        print("  kind     :", kind)
        print("  stream   :", stream[:90] + "..." if len(stream) > 90 else stream)
        print("  host     :", host)
        print("  headers  :", sorted(headers.keys()) if headers else "none")
        print("  duration :", info.get("duration"), "sec")
        print("  formats  :", len(info.get("formats") or []),
              "| hls:", sum(1 for f in info.get("formats") or [] if f.get("protocol") == "m3u8_native"))


if __name__ == "__main__":
    main()

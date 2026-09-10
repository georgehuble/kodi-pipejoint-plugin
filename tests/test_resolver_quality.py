# -*- coding: utf-8 -*-
"""Deterministic desktop checks for the resolver quality helpers.

No network: formats are fabricated and passed straight to the pure functions.
Covers the quality helpers of the `add-video-quality-selection` change plus the
InputStream Adaptive mapping helpers of the `fix-video-quality-selection` change.

Usage:  python3 tests/test_resolver_quality.py
"""

import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "lib"))

import resolver  # noqa: E402

PASSED = []


def check(name, cond):
    if not cond:
        print("FAIL: %s" % name)
        sys.exit(1)
    PASSED.append(name)
    print("  ok: %s" % name)


def fmt(protocol="https", vcodec="avc1", acodec="mp4a",
        height=None, url="https://example.com/stream", manifest_url=None, vbr=None):
    """Build a minimal yt-dlp-style format dict."""
    return {
        "protocol": protocol,
        "vcodec": vcodec,
        "acodec": acodec,
        "height": height,
        "url": url,
        "manifest_url": manifest_url,
        "vbr": vbr,
    }


def _make_video_formats():
    """Formats exposing heights 2160/1440/1080/720 + noise."""
    return [
        # audio-only: no video codec -> must be ignored by available_heights
        fmt(vcodec="none", acodec="mp4a", height=None, url="https://x/audio"),
        # adaptive video-only tracks
        fmt(protocol="m3u8_native", vcodec="avc1", acodec="none", height=2160,
            url="https://x/a2160", manifest_url="https://x/master.m3u8"),
        fmt(protocol="m3u8_native", vcodec="avc1", acodec="none", height=1440,
            url="https://x/a1440", manifest_url="https://x/master.m3u8"),
        # duplicate height 720 across two formats -> uniqueness matters
        fmt(vcodec="vp9", acodec="none", height=720, url="https://x/v720a"),
        fmt(vcodec="avc1", acodec="none", height=720, url="https://x/v720b"),
        # muxed progressive
        fmt(vcodec="avc1", acodec="mp4a", height=1080, url="https://x/p1080"),
    ]
    # note: 2160/1440 here come only from m3u8 (adaptive) rows


def test_available_heights():
    info = {"formats": _make_video_formats()}
    result = resolver.available_heights(info)
    check("1.1 available_heights sorted desc + unique",
          result == [2160, 1440, 1080, 720])
    check("1.1 available_heights ignores audio-only",
          resolver.available_heights({"formats": [fmt(vcodec="none", acodec="mp4a")]}) == [])
    check("1.1 available_heights empty formats -> []",
          resolver.available_heights({}) == [])


def test_height_label():
    for height, label in [(144, "144p"), (240, "240p"), (360, "360p"),
                          (480, "480p"), (720, "720p"), (1080, "1080p"),
                          (1440, "1440p"), (2160, "2160p")]:
        check("1.2 height_label(%d)==%r" % (height, label),
              resolver.height_label(height) == label)


def test_pick_progressive():
    info = {"formats": [
        fmt(vcodec="none", acodec="mp4a", height=None, url="https://x/audio"),
        fmt(vcodec="avc1", acodec="none", height=2160, url="https://x/v-only"),
        fmt(height=240, url="https://x/p240"),
        fmt(height=480, url="https://x/p480"),
        fmt(height=720, url="https://x/p720"),
        fmt(height=1080, url="https://x/p1080"),
    ]}

    url, _ = resolver.pick_progressive(info)
    check("1.3 pick_progressive default picks highest muxed (1080)",
          url == "https://x/p1080")

    url, _ = resolver.pick_progressive(info, max_height=720)
    check("1.3 pick_progressive max_height=720 picks 720",
          url == "https://x/p720")

    url, _ = resolver.pick_progressive(info, max_height=480)
    check("1.3 pick_progressive max_height=480 picks 480",
          url == "https://x/p480")

    url, _ = resolver.pick_progressive(info, max_height=100)
    check("1.3 pick_progressive cap below all muxed -> (None, None)",
          url is None)

    url, _ = resolver.pick_progressive({"formats": [fmt(vcodec="none", acodec="mp4a")]})
    check("1.3 pick_progressive audio-only -> (None, None)", url is None)


def test_resolve_video_max_height():
    info = {"formats": [
        fmt(vcodec="none", acodec="mp4a", height=None, url="https://x/audio"),
        fmt(vcodec="avc1", acodec="none", height=2160, url="https://x/v-only"),
        fmt(height=360, url="https://x/p360"),
        fmt(height=720, url="https://x/p720"),
        fmt(height=1080, url="https://x/p1080"),
    ]}
    # Stub extract so resolve_video works offline (progressive path).
    original_extract = resolver.extract
    resolver.extract = lambda url: info
    try:
        kind, stream, _, got_info = resolver.resolve_video(
            "VIDEO_ID", max_height=720)
        check("1.4 resolve_video max_height caps progressive fallback",
              kind == "progressive" and stream == "https://x/p720" and got_info is info)

        kind, stream, _, _ = resolver.resolve_video("VIDEO_ID", max_height=None)
        check("1.4 resolve_video no cap keeps best progressive",
              kind == "progressive" and stream == "https://x/p1080")
    finally:
        resolver.extract = original_extract

    # HLS path ignores max_height for the URL (cap is a player-layer property).
    hls_info = {"formats": [
        fmt(protocol="m3u8_native", vcodec="avc1", acodec="none", height=2160,
            url="https://x/hls2160", manifest_url="https://x/master.m3u8"),
        fmt(height=1080, url="https://x/p1080"),
    ]}
    resolver.extract = lambda url: hls_info
    try:
        kind, stream, _, _ = resolver.resolve_video("VIDEO_ID", max_height=720)
        check("1.4 resolve_video HLS URL unchanged under max_height",
              kind == "hls" and stream == "https://x/master.m3u8")
    finally:
        resolver.extract = original_extract


def test_isa_resolution_label():
    for height, label in [(2160, "4K"), (1440, "1440p"), (1080, "1080p"),
                          (720, "720p"), (640, "640p"), (480, "480p")]:
        check("isa_resolution_label(%d)==%r" % (height, label),
              resolver.isa_resolution_label(height) == label)
    # A request between two caps rounds down, so playback never exceeds it.
    check("isa_resolution_label(900) rounds down to 720p",
          resolver.isa_resolution_label(900) == "720p")
    check("isa_resolution_label(4000) rounds down to 4K",
          resolver.isa_resolution_label(4000) == "4K")
    for height in (360, 240, 144, 0, None):
        check("isa_resolution_label(%r) is None" % (height,),
              resolver.isa_resolution_label(height) is None)


def test_bandwidth_for_height():
    info = {"formats": [
        fmt(vcodec="none", acodec="mp4a", height=None, url="https://x/audio"),
        fmt(height=144, url="https://x/v144", vbr=80),
        fmt(height=240, url="https://x/v240", vbr=130),
        fmt(height=360, url="https://x/v360", vbr=250),
        fmt(height=720, url="https://x/v720"),  # bitrate unknown -> ignored
    ]}
    check("bandwidth_for_height(360) -> best at/below, in bit/s",
          resolver.bandwidth_for_height(info, 360) == 250000)
    check("bandwidth_for_height(240) -> 130000",
          resolver.bandwidth_for_height(info, 240) == 130000)
    check("bandwidth_for_height ignores formats without a bitrate",
          resolver.bandwidth_for_height(info, 100) is None)
    check("bandwidth_for_height(0/None) -> None",
          resolver.bandwidth_for_height(info, 0) is None
          and resolver.bandwidth_for_height(info, None) is None)


def test_selectable_heights():
    info = {"formats": _make_video_formats()}  # heights 2160/1440/1080/720
    check("selectable_heights hides >1080p by default",
          resolver.selectable_heights(info) == [1080, 720])
    check("selectable_heights shows all when higher resolutions are enabled",
          resolver.selectable_heights(info, show_higher_resolutions=True)
          == [2160, 1440, 1080, 720])
    check("selectable_heights empty formats -> []",
          resolver.selectable_heights({}) == [])


def main():
    print("=== resolver quality helpers ===")
    test_available_heights()
    test_height_label()
    test_pick_progressive()
    test_resolve_video_max_height()
    test_isa_resolution_label()
    test_bandwidth_for_height()
    test_selectable_heights()
    print("RESULT: OK (%d checks)" % len(PASSED))


if __name__ == "__main__":
    main()

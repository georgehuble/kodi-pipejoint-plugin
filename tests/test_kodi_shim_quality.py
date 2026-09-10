# -*- coding: utf-8 -*-
"""Deterministic Kodi-shim checks for the quality-selection router paths.

Runs [`default.py`](../default.py) exactly as Kodi would (see
[`kodi_shim.py`](kodi_shim.py)) with a fake resolver, configurable add-on
settings and a configurable `Dialog.select`. Covers the
`fix-video-quality-selection` change:

* a concrete quality is pinned with InputStream Adaptive's stream-selection
  properties (`fixed-res` + `chooser_resolution_max`), never `max_resolution`;
* Auto/Best asks for adaptive selection and sets no cap;
* a height below the smallest fixable resolution falls back to a bandwidth cap;
* the dialog lists selectable heights only (1440p/2160p gated by a setting);
* the progressive fallback still receives `max_height`.

Usage:  python3 tests/test_kodi_shim_quality.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kodi_shim import FakeResolver, Harness, Reporter  # noqa: E402

STREAM_SELECTION = "inputstream.adaptive.stream_selection_type"
RESOLUTION_MAX = "inputstream.adaptive.chooser_resolution_max"
BANDWIDTH_MAX = "inputstream.adaptive.chooser_bandwidth_max"
LEGACY_MAX_RESOLUTION = "inputstream.adaptive.max_resolution"

#: Ladder used by most checks (includes heights above 1080p for the gating test).
LADDER = (2160, 1440, 1080, 720, 360)
#: Video bitrates in kbit/s, for the sub-480p bandwidth fallback.
RATES = {360: 250, 240: 130, 144: 80}


def harness(kind="hls", heights=LADDER, settings=None):
    h = Harness()
    h.resolver = FakeResolver(heights=heights, kind=kind, rates=RATES)
    if settings:
        h.settings.update(settings)
    return h


def test_default_is_adaptive(r):
    h = harness()
    h.run("?action=play&video_id=abc")
    item = h.item()
    r.check("default Auto/Best -> stream_selection_type=adaptive",
            item.props.get(STREAM_SELECTION) == "adaptive")
    r.check("default Auto/Best -> no chooser cap",
            RESOLUTION_MAX not in item.props and BANDWIDTH_MAX not in item.props)
    r.check("default Auto/Best -> resolver max_height None",
            h.resolver.calls[0][1] is None)
    r.check("legacy max_resolution is never set",
            LEGACY_MAX_RESOLUTION not in item.props)


def test_default_setting_pins_quality(r):
    h = harness(settings={"default_quality": "1080p"})
    h.run("?action=play&video_id=abc")
    item = h.item()
    r.check("default 1080p -> fixed-res",
            item.props.get(STREAM_SELECTION) == "fixed-res")
    r.check("default 1080p -> chooser_resolution_max=1080p",
            item.props.get(RESOLUTION_MAX) == "1080p")
    r.check("default 1080p -> resolver max_height 1080",
            h.resolver.calls[0][1] == 1080)


def test_url_quality_pins_quality(r):
    h = harness()
    h.run("?action=play&video_id=abc&quality=720")
    item = h.item()
    r.check("quality=720 -> fixed-res + 720p",
            item.props.get(STREAM_SELECTION) == "fixed-res"
            and item.props.get(RESOLUTION_MAX) == "720p")
    r.check("quality=720 -> resolver max_height 720", h.resolver.calls[0][1] == 720)
    r.check("quality=720 -> no dialog on a plain play", h.dialog_calls == [])


def test_low_quality_uses_bandwidth_cap(r):
    h = harness()
    h.run("?action=play&video_id=abc&quality=360")
    item = h.item()
    r.check("quality=360 -> adaptive (nothing below 480p can be fixed)",
            item.props.get(STREAM_SELECTION) == "adaptive")
    r.check("quality=360 -> no resolution cap", RESOLUTION_MAX not in item.props)
    r.check("quality=360 -> bandwidth ceiling 250000 bit/s",
            item.props.get(BANDWIDTH_MAX) == "250000")
    r.check("quality=360 -> resolver max_height 360", h.resolver.calls[0][1] == 360)


def test_quality_label_mapping(r):
    for raw, label in (("1080", "1080p"), ("720p", "720p"), ("480", "480p"),
                       ("640", "640p")):
        h = harness(settings={"default_quality": raw})
        h.run("?action=play&video_id=abc")
        r.check("setting %r -> %s" % (raw, label),
                h.item().props.get(RESOLUTION_MAX) == label)
    for raw in ("Auto/Best", "0", ""):
        h = harness(settings={"default_quality": raw})
        h.run("?action=play&video_id=abc")
        r.check("setting %r -> adaptive" % raw,
                h.item().props.get(STREAM_SELECTION) == "adaptive")


def test_dialog_hides_high_resolutions_by_default(r):
    h = harness()
    h.dialog_selection = 0
    h.run("?action=play_quality&video_id=abc")
    r.check("dialog hides 1440p/2160p by default",
            h.dialog_calls and
            h.dialog_calls[0][1] == ["Auto/Best", "1080p", "720p", "360p"])


def test_dialog_shows_high_resolutions_when_enabled(r):
    h = harness(settings={"show_higher_resolutions": "On"})
    h.dialog_selection = 0
    h.run("?action=play_quality&video_id=abc")
    r.check("dialog shows 1440p/2160p when enabled",
            h.dialog_calls and
            h.dialog_calls[0][1] ==
            ["Auto/Best", "2160p", "1440p", "1080p", "720p", "360p"])


def test_picked_quality_is_fixed(r):
    h = harness()
    h.dialog_selection = 2  # [Auto/Best, 1080p, 720p, 360p] -> 720p
    h.run("?action=play_quality&video_id=abc")
    item = h.item()
    r.check("picked 720p -> fixed-res + 720p",
            item.props.get(STREAM_SELECTION) == "fixed-res"
            and item.props.get(RESOLUTION_MAX) == "720p")
    r.check("exactly one resolve per invocation (one-shot)",
            len([call for call in h.resolver.calls if call[0] == "abc"]) == 1)


def test_picked_auto_is_adaptive(r):
    h = harness()
    h.dialog_selection = 0
    h.run("?action=play_quality&video_id=abc")
    item = h.item()
    r.check("picked Auto/Best -> adaptive, no cap",
            item.props.get(STREAM_SELECTION) == "adaptive"
            and RESOLUTION_MAX not in item.props)


def test_cancel_starts_nothing(r):
    h = harness()
    h.dialog_selection = -1
    h.run("?action=play_quality&video_id=abc")
    r.check("cancel leaves setResolvedUrl un-called", h.resolved == [])


def test_progressive_fallback(r):
    h = harness(kind="progressive")
    h.run("?action=play&video_id=abc&quality=720")
    item = h.item()
    r.check("progressive -> resolver got max_height 720",
            h.resolver.calls[0][1] == 720)
    r.check("progressive -> no stream-selection properties",
            STREAM_SELECTION not in item.props
            and RESOLUTION_MAX not in item.props
            and BANDWIDTH_MAX not in item.props)


def main():
    r = Reporter("shim: quality selection via ISA stream-selection properties")
    test_default_is_adaptive(r)
    test_default_setting_pins_quality(r)
    test_url_quality_pins_quality(r)
    test_low_quality_uses_bandwidth_cap(r)
    test_quality_label_mapping(r)
    test_dialog_hides_high_resolutions_by_default(r)
    test_dialog_shows_high_resolutions_when_enabled(r)
    test_picked_quality_is_fixed(r)
    test_picked_auto_is_adaptive(r)
    test_cancel_starts_nothing(r)
    test_progressive_fallback(r)
    r.done()


if __name__ == "__main__":
    main()

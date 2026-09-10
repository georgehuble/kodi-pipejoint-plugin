# -*- coding: utf-8 -*-
"""Deterministic desktop checks for the resolver audio/subtitle helpers.

No network: formats / subtitles are fabricated and passed straight to the pure
functions. Covers tasks 1.1-1.5 of the add-audio-subtitle-defaults change and
the improved original-audio detection plus the track-picking / target-language
helpers added by the fix-original-audio-selection change.

Usage:  python3 tests/test_resolver_audio_subtitles.py
"""

import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "lib")
)

import resolver  # noqa: E402

PASSED = []


def check(name, cond):
    if not cond:
        print("FAIL: %s" % name)
        sys.exit(1)
    PASSED.append(name)
    print("  ok: %s" % name)


def audio_fmt(language, note=None, acodec="mp4a", vcodec="none", preference=None):
    """Audio-only format dict; audio tracks have no video codec."""
    fmt = {"acodec": acodec, "vcodec": vcodec, "language": language}
    if note is not None:
        fmt["format_note"] = note
    if preference is not None:
        fmt["language_preference"] = preference
    return fmt


def track(language=None, name=None, codec=None):
    """Player-reported audio track double, all keys optional."""
    entry = {}
    if language is not None:
        entry["language"] = language
    if name is not None:
        entry["name"] = name
    if codec is not None:
        entry["codec"] = codec
    return entry


def video_fmt(language=None):
    """Muxed / video-carrying format, never an audio-only track."""
    return {"acodec": "mp4a", "vcodec": "avc1", "language": language, "height": 720}


def sub_record(url, ext):
    return {"url": url, "ext": ext}


# --- 1.1 audio_languages ----------------------------------------------------


def test_audio_languages():
    print("task 1.1: audio_languages")
    info = {
        "formats": [
            audio_fmt("en", note="English (US) original (default)"),
            audio_fmt("ru"),
            audio_fmt("en", note="dubbed-auto"),  # duplicate language -> unique
            video_fmt(),  # carries video codec -> skipped
        ]
    }
    check(
        "1.1 unique languages in first-seen order", resolver.audio_languages(info) == ["en", "ru"]
    )
    check(
        "1.1 muxed video formats ignored",
        resolver.audio_languages({"formats": [video_fmt("ru")]}) == [],
    )
    check("1.1 empty formats -> []", resolver.audio_languages({}) == [])
    check("1.1 no formats key -> []", resolver.audio_languages({"title": "x"}) == [])


# --- 1.2 original_audio_language -------------------------------------------


def test_original_audio_language():
    print("task 1.2: original_audio_language")
    # Russian original (with marker) + English auto/dubbed track.
    info = {
        "formats": [
            audio_fmt("ru", note="Russian original"),
            audio_fmt("en", note="dubbed-auto"),
        ]
    }
    check("1.2 original by marker wins over auto", resolver.original_audio_language(info) == "ru")

    # yt-dlp marks the original with language_preference 10, the dub with 5.
    pref = {
        "formats": [
            audio_fmt("en", note="dubbed-auto", preference=5),
            audio_fmt("ru", note="Russian", preference=10),
        ]
    }
    check(
        "1.2 language_preference 10 beats preference 5",
        resolver.original_audio_language(pref) == "ru",
    )

    # A "(default)" dub is NOT the original: a separate original track wins
    # regardless of the order in the format list.
    info2 = {
        "formats": [
            audio_fmt("en-US", note="English (US) (default)"),
            audio_fmt("ru", note="Original"),
        ]
    }
    check(
        "1.2 '(default)' dub does not win over a separate original",
        resolver.original_audio_language(info2) == "ru",
    )

    # With only a "(default)" track and no explicit original, the default is a
    # weak fallback (better than nothing).
    info2b = {
        "formats": [
            audio_fmt("en-US", note="English (US) (default)"),
            audio_fmt("ru"),
        ]
    }
    check(
        "1.2 '(default)' used as a weak fallback",
        resolver.original_audio_language(info2b) == "en-US",
    )

    # No markers, two languages -> original unknown (None).
    info3 = {
        "formats": [
            audio_fmt("en"),
            audio_fmt("ru"),
        ]
    }
    check(
        "1.2 no markers, multiple languages -> None",
        resolver.original_audio_language(info3) is None,
    )

    # No markers, single language -> fallback to that language.
    info4 = {"formats": [audio_fmt("de")]}
    check(
        "1.2 no markers, single language falls back",
        resolver.original_audio_language(info4) == "de",
    )

    # No audio tracks at all -> None.
    check(
        "1.2 no tracks -> None",
        resolver.original_audio_language({"formats": [video_fmt()]}) is None,
    )
    check("1.2 empty info -> None", resolver.original_audio_language({}) is None)


# --- fix-original-audio-selection: pick_audio_track -------------------------


def test_pick_audio_track():
    print("task 1.3 (fix-original-audio): pick_audio_track")
    # Original ru (AAC-LC + HE-AAC) and dubbed en (AAC-LC + HE-AAC).
    tracks = [
        track("ru", "Russian original", "aac-lc"),
        track("ru", "Russian original", "he-aac"),
        track("en", "English dubbed", "aac-lc"),
        track("en", "English dubbed", "he-aac"),
    ]
    check(
        "1.3 target ru picks a ru rendition, not the en dub",
        resolver.pick_audio_track("ru", tracks) == 0,
    )
    check("1.3 target en picks an en rendition", resolver.pick_audio_track("en", tracks) == 2)

    # Among renditions of one language AAC-LC beats HE-AAC regardless of order.
    only_en = [
        track("en", "English", "he-aac"),
        track("en", "English", "aac-lc"),
    ]
    check("1.3 AAC-LC preferred over HE-AAC", resolver.pick_audio_track("en", only_en) == 1)

    # Region-insensitive language matching, both directions and normalisation.
    check(
        "1.3 bare language matches a region variant",
        resolver.pick_audio_track("en-US", [track("en", "English")]) == 0,
    )
    check(
        "1.3 region target matches a bare track language",
        resolver.pick_audio_track("ru", [track("ru-RU", "Russian")]) == 0,
    )
    check(
        "1.3 underscores and case are normalised",
        resolver.pick_audio_track("pt_BR", [track("PT-br", "Portuguese")]) == 0,
    )

    # ISO 639-1 <-> ISO 639-2/T forms of one language match (ru <-> rus).
    check(
        "1.3 two-letter target matches a three-letter track (ru -> rus)",
        resolver.pick_audio_track("ru", [track("rus", "Russian")]) == 0,
    )
    check(
        "1.3 two-letter target matches a three-letter track (en -> eng)",
        resolver.pick_audio_track("en", [track("eng", "English")]) == 0,
    )
    check(
        "1.3 three-letter target matches a two-letter track (rus -> ru)",
        resolver.pick_audio_track("rus", [track("ru", "Russian")]) == 0,
    )
    # Real kodi.log case: a two-letter original among three-letter tracks, with
    # English dubs listed first (must not win by position).
    log_tracks = [track("en-US"), track("en-US"), track("rus"), track("rus")]
    check(
        "1.3 ru target skips the leading en-US dubs for a rus track",
        resolver.pick_audio_track("ru", log_tracks) in (2, 3),
    )

    # Descriptive / audio-description tracks are ignored.
    desc = [
        track("en", "English descriptive", "aac-lc"),
        track("en", "English", "aac-lc"),
    ]
    check("1.3 descriptive track ignored", resolver.pick_audio_track("en", desc) == 1)

    # The original role wins over the codec rank.
    role = [
        track("ru", "Russian dubbed", "aac-lc"),
        track("ru", "Russian original", "he-aac"),
    ]
    check("1.3 original role preferred over codec rank", resolver.pick_audio_track("ru", role) == 1)

    check("1.3 no matching language -> None", resolver.pick_audio_track("de", tracks) is None)
    check("1.3 empty target -> None", resolver.pick_audio_track(None, tracks) is None)
    check("1.3 empty tracks -> None", resolver.pick_audio_track("ru", []) is None)
    check(
        "1.3 track without a language is ignored",
        resolver.pick_audio_track("ru", [track(name="?", codec="aac")]) is None,
    )


# --- fix-original-audio-selection: target_audio_language --------------------


def test_target_audio_language():
    print("task 1.4 (fix-original-audio): target_audio_language")
    check("1.4 auto -> None", resolver.target_audio_language("auto", None) is None)
    check("1.4 auto ignores a stray language", resolver.target_audio_language("auto", "ru") is None)
    check(
        "1.4 original -> detected language",
        resolver.target_audio_language("original", "ru") == "ru",
    )
    check(
        "1.4 explicit tag returned as-is",
        resolver.target_audio_language("language", "en-US") == "en-US",
    )
    check(
        "1.4 original with no detected language -> None",
        resolver.target_audio_language("original", None) is None,
    )


# --- fix-audio-language-code-match: ISO 639 code forms -----------------------


def test_language_code_form():
    print("task 1.1 (fix-audio-language): ISO 639 code form")
    check(
        "1.1 two-letter canonicalised to three-letter (ru -> rus)",
        resolver._language_code_form("ru") == "rus",
    )
    check(
        "1.1 three-letter stays three-letter (rus -> rus)",
        resolver._language_code_form("rus") == "rus",
    )
    check(
        "1.1 en <-> eng compare equal",
        resolver._language_code_form("en") == resolver._language_code_form("eng") == "eng",
    )
    check(
        "1.1 region is dropped for the comparison form",
        resolver._language_code_form("ru-RU") == "rus",
    )
    check(
        "1.1 unknown code returned unchanged",
        resolver._language_code_form("xx") == "xx"
        and resolver._language_code_form("qq-ZZ") == "qq-ZZ",
    )


def test_isa_audio_language():
    print("task 1.3 (fix-audio-language): ISA hint code form")
    check("1.3 ru -> rus", resolver.isa_audio_language("ru") == "rus")
    check("1.3 en-US -> eng", resolver.isa_audio_language("en-US") == "eng")
    check("1.3 unknown returned unchanged", resolver.isa_audio_language("xx") == "xx")
    check("1.3 empty stays empty", resolver.isa_audio_language("") == "")


def test_audio_language_supported():
    print("task 1.2 (fix-audio-language): audio_language_supported")
    info = {"formats": [audio_fmt("rus"), audio_fmt("en")]}
    check("1.2 ru exposed by a rus track", resolver.audio_language_supported(info, "ru"))
    check("1.2 en exposed by an en track", resolver.audio_language_supported(info, "en"))
    check(
        "1.2 unavailable language is not exposed",
        not resolver.audio_language_supported(info, "de"),
    )
    check("1.2 empty target is not exposed", not resolver.audio_language_supported(info, None))


# --- 1.3 subtitle_languages -------------------------------------------------


def test_subtitle_languages():
    print("task 1.3: subtitle_languages")
    info = {
        "subtitles": {
            "en": [sub_record("https://s/en.vtt", "vtt")],
            "ru": [sub_record("https://s/ru.vtt", "vtt")],
        },
        "automatic_captions": {
            "en": [sub_record("https://s/en.auto.vtt", "vtt")],  # dup lang
            "uk": [sub_record("https://s/uk.vtt", "vtt")],
        },
    }
    check(
        "1.3 union of subtitles + automatic_captions",
        resolver.subtitle_languages(info) == ["en", "ru", "uk"],
    )
    check("1.3 no subtitle keys -> []", resolver.subtitle_languages({}) == [])
    check(
        "1.3 only automatic_captions",
        resolver.subtitle_languages({"automatic_captions": {"de": []}}) == ["de"],
    )


# --- 1.4 subtitle_url -------------------------------------------------------


def test_subtitle_url():
    print("task 1.4: subtitle_url")
    info = {
        "subtitles": {
            "ru": [sub_record("https://s/ru.vtt", "vtt")],
            "en": [
                sub_record("https://s/en.vtt", "vtt"),
                sub_record("https://s/en.srv3", "srv3"),
            ],
        },
        "automatic_captions": {
            "en": [sub_record("https://s/en.auto.srv3", "srv3")],
            "de": [sub_record("https://s/de.json3", "json3")],
        },
    }
    check("1.4 prefers vtt over srv3", resolver.subtitle_url(info, "en") == "https://s/en.vtt")
    check(
        "1.4 falls back to srv3 when no vtt",
        resolver.subtitle_url(info, "ru") == "https://s/ru.vtt",
    )
    check(
        "1.4 manual subtitles preferred over auto for same ext",
        resolver.subtitle_url(info, "en") == "https://s/en.vtt",
    )
    check("1.4 only json3 -> None (skipped)", resolver.subtitle_url(info, "de") is None)
    check("1.4 unknown language -> None", resolver.subtitle_url(info, "xx") is None)


# --- 1.5 playable_subtitle_urls --------------------------------------------


def test_playable_subtitle_urls():
    print("task 1.5: playable_subtitle_urls")
    info = {
        "subtitles": {
            "ru": [sub_record("https://s/ru.vtt", "vtt")],
            "en": [sub_record("https://s/en.json3", "json3")],  # unplayable
        },
    }
    check(
        "1.5 explicit language returns its playable url",
        resolver.playable_subtitle_urls(info, "ru") == ["https://s/ru.vtt"],
    )
    check("1.5 json3-only language -> []", resolver.playable_subtitle_urls(info, "en") == [])
    # First available playable language: ru (vtt), because en is json3-only.
    check(
        "1.5 no lang -> first playable language",
        resolver.playable_subtitle_urls(info) == ["https://s/ru.vtt"],
    )
    check(
        "1.5 nothing playable -> []",
        resolver.playable_subtitle_urls({"subtitles": {"en": []}}) == [],
    )
    check("1.5 no subtitles -> []", resolver.playable_subtitle_urls({}) == [])


def main():
    print("=== resolver audio/subtitle helpers ===")
    test_audio_languages()
    test_original_audio_language()
    test_pick_audio_track()
    test_target_audio_language()
    test_language_code_form()
    test_isa_audio_language()
    test_audio_language_supported()
    test_subtitle_languages()
    test_subtitle_url()
    test_playable_subtitle_urls()
    print("RESULT: OK (%d checks)" % len(PASSED))


if __name__ == "__main__":
    main()

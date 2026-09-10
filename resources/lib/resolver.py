# -*- coding: utf-8 -*-
"""Stream resolution via bundled yt-dlp.

Deliberately free of any xbmc import so the logic can be exercised on a normal
desktop with test_desktop.py, without a running Kodi (same trick as ytdlpcast,
MIT).

Strategy:
  1. prefer the HLS master manifest (m3u8) -> handed to InputStream Adaptive,
     which gives seeking + bitrate switching off a single URL;
  2. else a muxed progressive format (https) as a fallback.
"""

import urllib.parse

from yt_dlp import YoutubeDL
from yt_dlp.utils import ISO639Utils

HLS_MIME = "application/vnd.apple.mpegurl"
DASH_MIME = "application/dash+xml"

# Headers yt-dlp attaches for its own use; forwarding them to InputStream
# Adaptive is at best useless and at worst breaks the manifest request.
_SKIP_HEADERS = ("cookie", "youtubei")


def watch_url(video_id):
    return "https://www.youtube.com/watch?v={}".format(video_id)


def extract(url, extra_opts=None):
    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
    }
    if extra_opts:
        options.update(extra_opts)
    with YoutubeDL(options) as ydl:
        return ydl.sanitize_info(ydl.extract_info(url, download=False))


def pick_hls(info):
    """(manifest_url, headers) of the HLS master playlist, or (None, None)."""
    for fmt in info.get("formats") or ():
        if fmt.get("protocol") == "m3u8_native" and fmt.get("manifest_url"):
            return fmt["manifest_url"], fmt.get("http_headers") or {}
    return None, None


def available_heights(info):
    """Unique heights (descending) of formats that carry a video codec.

    Formats are video-only adaptive and muxed alike; anything without a video
    codec (audio-only) is ignored. Pure helper: no xbmc, no network.
    """
    seen = set()
    for fmt in info.get("formats") or ():
        if fmt.get("vcodec") in (None, "none"):
            continue
        height = fmt.get("height")
        if height:
            seen.add(int(height))
    return sorted(seen, reverse=True)


def height_label(height):
    """Standard label for a video height, e.g. 720 -> "720p"."""
    return "%dp" % int(height)


#: Video resolution caps InputStream Adaptive understands, label -> pixel
#: height. Taken from InputStream Adaptive's own settings (src/CompSettings.h,
#: RES_CONV_LIST): "480p" is 640x480, "640p" is 960x640, "720p" is 1280x720 and
#: so on. Descending, so a lookup finds the largest cap at or below a request.
ISA_RESOLUTION_HEIGHTS = (
    ("4K", 2160),
    ("1440p", 1440),
    ("1080p", 1080),
    ("720p", 720),
    ("640p", 640),
    ("480p", 480),
)

#: Heights above this are hidden unless the user opts in (NewPipe hides 1440p
#: and 2160p by default).
HIGH_RESOLUTION_THRESHOLD = 1080


def isa_resolution_label(height):
    """InputStream Adaptive cap label for `height`, or None when too low.

    Returns the largest supported cap whose pixel height does not exceed the
    requested height, so playback can never be forced above the request. None
    means no supported cap is low enough (below 480p) and a bandwidth ceiling
    must be used instead. Pure helper: no xbmc, no network.
    """
    if not height:
        return None
    for label, cap_height in ISA_RESOLUTION_HEIGHTS:
        if cap_height <= int(height):
            return label
    return None


def bandwidth_for_height(info, height):
    """Bitrate (bit/s) of the best video rendition at or below `height`.

    Used when the requested height sits below InputStream Adaptive's smallest
    resolution cap: the ceiling is then expressed as bandwidth instead. yt-dlp
    reports `vbr`/`tbr` in kbit/s, so the result is converted to bit/s. Returns
    None when no rendition at or below the height carries a bitrate.
    Pure helper: no xbmc, no network.
    """
    if not height:
        return None
    best = None
    for fmt in info.get("formats") or ():
        if fmt.get("vcodec") in (None, "none"):
            continue
        fmt_height = fmt.get("height") or 0
        if not fmt_height or fmt_height > int(height):
            continue
        rate = fmt.get("vbr") or fmt.get("tbr") or 0
        if rate and (best is None or rate > best):
            best = rate
    if best is None:
        return None
    return int(best * 1000)


def selectable_heights(info, show_higher_resolutions=False):
    """Heights to offer in the quality dialog, highest first.

    Identical to `available_heights`, except heights above 1080p are dropped
    unless `show_higher_resolutions` is set - the NewPipe default of hiding
    1440p/2160p behind an opt-in. Pure helper: no xbmc, no network.
    """
    heights = available_heights(info)
    if show_higher_resolutions:
        return heights
    return [height for height in heights if height <= HIGH_RESOLUTION_THRESHOLD]


def pick_progressive(info, max_height=None):
    """Best single muxed file carrying both audio and video, or (None, None).

    With max_height given, only muxed formats up to that height are considered,
    so the caller can cap a progressive fallback to a chosen resolution.
    """
    best = None
    for fmt in info.get("formats") or ():
        if fmt.get("protocol") not in ("https", "http"):
            continue
        if fmt.get("vcodec") in (None, "none") or fmt.get("acodec") in (None, "none"):
            continue
        height = fmt.get("height") or 0
        if max_height and height > max_height:
            continue
        if best is None or height > (best.get("height") or 0):
            best = fmt
    if best is None:
        return None, None
    return best["url"], best.get("http_headers") or {}


def resolve_video(video_id_or_url, allow_progressive=True, max_height=None):
    """One-shot helper: return (kind, stream, headers, info).

    kind is 'hls' or 'progressive'. Raises on failure.

    max_height only affects the progressive fallback (it is passed to
    pick_progressive); the HLS URL is not changed because capping an adaptive
    stream happens at the player layer (InputStream Adaptive property).
    """
    url = video_id_or_url if "://" in video_id_or_url else watch_url(video_id_or_url)
    info = extract(url)

    stream, headers = pick_hls(info)
    if stream is not None:
        return "hls", stream, headers, info

    if allow_progressive:
        stream, headers = pick_progressive(info, max_height=max_height)
        if stream is not None:
            return "progressive", stream, headers, info

    raise RuntimeError("no playable stream (no HLS, no progressive)")


def _audio_only_formats(info):
    """Audio-only formats: an audio codec and no video codec. Pure helper."""
    for fmt in info.get("formats") or ():
        if fmt.get("acodec") in (None, "none"):
            continue
        if fmt.get("vcodec") not in (None, "none"):
            continue
        yield fmt


def audio_languages(info):
    """Unique languages of the audio-only formats, in first-seen order.

    A format is audio-only when it carries an audio codec and no video codec.
    Pure helper: no xbmc, no network.
    """
    seen = []
    for fmt in _audio_only_formats(info):
        lang = fmt.get("language")
        if lang and lang not in seen:
            seen.append(lang)
    return seen


#: yt-dlp `language_preference` value that marks the video's original track.
ORIGINAL_PREFERENCE = 10
#: yt-dlp `language_preference` value that marks the "default" track - for
#: YouTube often an auto-dub, not the original.
DEFAULT_PREFERENCE = 5


def _language_preference(fmt):
    """`language_preference` as an int, or None when absent/unusable."""
    try:
        return int(fmt.get("language_preference"))
    except (TypeError, ValueError):
        return None


def original_audio_language(info):
    """Language of the video's original audio track, or None.

    A track is the original when yt-dlp marks it with `language_preference` 10
    or its format_note carries an "original" marker. The "(default)" marker and
    `language_preference` 5 mark the "default" track, which for YouTube is often
    an auto-dub rather than the original; they are only a weak fallback used
    when no explicit original exists. Without any marker the fallback is a video
    that exposes exactly one audio language; otherwise the original is unknown
    and None is returned (caller falls back to Auto). Pure helper: no xbmc.
    """
    default_language = None
    for fmt in _audio_only_formats(info):
        language = fmt.get("language")
        if not language:
            continue
        note = (fmt.get("format_note") or "").lower()
        preference = _language_preference(fmt)
        if preference == ORIGINAL_PREFERENCE or "original" in note:
            return language
        if default_language is None and (preference == DEFAULT_PREFERENCE or "(default)" in note):
            default_language = language
    if default_language is not None:
        return default_language
    languages = audio_languages(info)
    if len(languages) == 1:
        return languages[0]
    return None


def target_audio_language(mode, lang):
    """Language to match against the player's tracks, or None.

    Turns a resolved audio preference (mode/lang, see default.audio_preference)
    into the tag the post-start selection compares against: Auto (or a mode that
    resolved to no language) yields None, leaving the player's own choice alone;
    an "original" or explicit "language" preference yields the concrete tag.
    Pure helper: no xbmc, no network.
    """
    if mode == "auto" or not lang:
        return None
    return lang


#: Codec ranks for renditions of one language: plain AAC-LC is preferred,
#: HE-AAC (SBR) comes last, and anything unknown sits in between.
_CODEC_AAC_LC = 0
_CODEC_UNKNOWN = 1
_CODEC_HE_AAC = 2


def _normalize_language(language):
    """Lower-cased language tag with underscores turned into dashes."""
    return (language or "").strip().lower().replace("_", "-")


def _base_language(language):
    """Primary subtag of a language tag ("ru-RU" -> "ru")."""
    return _normalize_language(language).split("-", 1)[0]


def _iso639_long(primary):
    """ISO 639-2/T (three-letter) form of a primary subtag, or None.

    Uses the vendored yt-dlp language table as the single source of truth. None
    means the subtag is unknown to the table (or the table is unusable), so
    callers keep the original value rather than inventing an equivalence.
    """
    code = (primary or "").strip().lower()
    if not code:
        return None
    short2long = getattr(ISO639Utils, "short2long", None)
    long2short = getattr(ISO639Utils, "long2short", None)
    if short2long is None:
        return None
    try:
        if long2short is not None and long2short(code):
            return code  # already an ISO 639-2/T form
        return short2long(code) or None
    except Exception:  # noqa: BLE001 - a broken table must not break matching
        return None


def _language_code_form(language):
    """Language tag reduced to one ISO 639 form, for equivalence comparison.

    The primary subtag is lower-cased with "_" treated as "-" (see
    `_base_language`) and mapped to its ISO 639-2/T form when the vendored table
    knows it, so `ru` and `rus` (likewise `en` and `eng`) compare equal. A code
    the table does not know is returned unchanged, so no false equivalences are
    introduced. Pure helper: no xbmc, no network.
    """
    base = _base_language(language)
    if not base:
        return language
    return _iso639_long(base) or language


def isa_audio_language(language):
    """Language code to hand InputStream Adaptive so its hint can match.

    Manifests and the player commonly announce an audio rendition with the
    three-letter ISO 639-2/T code (`rus`) while the resolver detects the
    two-letter one (`ru`); requesting the same form lets the pre-playback hint
    match. Only the primary subtag is converted (the property takes a plain
    language code, so a region is dropped) and a language without a known
    three-letter form is returned unchanged. The hint stays best-effort and
    never blocks playback. Pure helper: no xbmc, no network.
    """
    return _language_code_form(language)


def _language_matches(target, track_language):
    """True when a track language matches `target`, region-insensitively.

    Comparison ignores case, treats "_" as "-", matches a bare language against
    any region variant of it (ru <-> ru-RU) and equates the ISO 639-1 and
    ISO 639-2/T forms of one language (ru <-> rus), so an explicit two-letter
    tag still finds the track when the video spells it with three letters.
    """
    base = _base_language(target)
    if not base:
        return False
    normalized = _normalize_language(track_language)
    if not normalized:
        return False
    if normalized == _normalize_language(target):
        return True
    if _base_language(track_language) == base:
        return True
    return _language_code_form(target) == _language_code_form(track_language)


def audio_language_supported(info, lang):
    """True when the video exposes an audio language equivalent to `lang`.

    Uses the same language matching as the post-start selection, so a
    two-letter request counts as exposed when the manifest spells the language
    with a three-letter code (and vice versa). Pure helper: no xbmc, no network.
    """
    if not lang:
        return False
    return any(_language_matches(lang, candidate) for candidate in audio_languages(info))


def _is_descriptive(track):
    """True for audio-description / descriptive service tracks."""
    name = (track.get("name") or "").lower()
    return "desc" in name or "descriptive" in name


def _is_original_track(track):
    """True when the track advertises the original role in its name/note."""
    text = ("%s %s" % (track.get("name") or "", track.get("note") or "")).lower()
    return "original" in text


def _codec_rank(codec):
    """Preference rank of an audio codec: AAC-LC, unknown, then HE-AAC."""
    text = (codec or "").strip().lower().replace("_", "-")
    if not text or text == "none":
        return _CODEC_UNKNOWN
    if "he-aac" in text or "heaac" in text:
        return _CODEC_HE_AAC
    if "aac" in text:
        return _CODEC_AAC_LC
    return _CODEC_UNKNOWN


def pick_audio_track(target_lang, tracks):
    """Index of the player audio track to select, or None.

    `target_lang` is a language tag (e.g. "ru", "en-US"); `tracks` is a list of
    player-reported audio tracks, each a mapping with the optional keys
    "language", "name" and "codec". Matching is language-first and independent
    of the track order: languages compare region-insensitively (see
    `_language_matches`) and descriptive/audio-description tracks are ignored.
    Among the tracks of the requested language the "original" role is preferred,
    then AAC-LC ahead of HE-AAC; ties keep the earliest track. Returns the index
    into `tracks`, or None when nothing matches (the caller then leaves the
    choice to the player). Pure helper: no xbmc, no network.
    """
    if not target_lang:
        return None
    best_index = None
    best_rank = None
    for index, track in enumerate(tracks or ()):
        if _is_descriptive(track):
            continue
        if not _language_matches(target_lang, track.get("language")):
            continue
        rank = (0 if _is_original_track(track) else 1, _codec_rank(track.get("codec")))
        if best_rank is None or rank < best_rank:
            best_index, best_rank = index, rank
    return best_index


def subtitle_languages(info):
    """Languages of all subtitle/caption tracks, first-seen order.

    Union of the manually authored `subtitles` and the automatically generated
    `automatic_captions` exposed by yt-dlp. Pure helper.
    """
    seen = []
    for key in ("subtitles", "automatic_captions"):
        for lang in info.get(key) or {}:
            if lang and lang not in seen:
                seen.append(lang)
    return seen


def subtitle_url(info, lang):
    """Playable subtitle URL for a language, or None if none is usable.

    Prefers a webvtt (ext == "vtt") record, then "srv3"; "json3" is skipped
    because the Kodi player cannot parse YouTube's json3 captions. Manual
    subtitles are considered before automatic captions for the same format.
    """
    preferred = ("vtt", "srv3")
    for ext in preferred:
        for key in ("subtitles", "automatic_captions"):
            for record in (info.get(key) or {}).get(lang) or ():
                if record.get("ext") == ext and record.get("url"):
                    return record["url"]
    return None


def playable_subtitle_urls(info, lang=None):
    """URLs that can be attached to the Kodi player as external subtitles.

    With lang, returns the playable URL for that language (or []). Without
    lang, returns the playable URL of the first available language. "Playable"
    means a format the player can render (see subtitle_url). Pure helper.
    """
    if lang:
        url = subtitle_url(info, lang)
        return [url] if url else []
    for candidate in subtitle_languages(info):
        url = subtitle_url(info, candidate)
        if url:
            return [url]
    return []


def encode_headers(headers):
    """Headers in the 'a=b&c=d' shape InputStream Adaptive expects."""
    usable = {
        key: value
        for key, value in (headers or {}).items()
        if value and not key.lower().startswith(_SKIP_HEADERS)
    }
    return urllib.parse.urlencode(usable)

# -*- coding: utf-8 -*-
"""Catalog access (video search / channel search / channel uploads) via yt-dlp.

xbmc-free so it can be exercised on a desktop with the test scripts.
Every function returns plain dicts / lists of dicts (no yt-dlp objects, no
giant format payloads) so the UI layer stays light and fast.
"""

import re
import urllib.parse

from yt_dlp import YoutubeDL

#: A YouTube video id (11 chars); channel/playlist ids do not match this.
_VIDEO_ID = re.compile(r"^[\w-]{11}$")

#: YouTube search filter "Channels only" (the `sp` parameter, URL-encoded).
#: Verified against the bundled YoutubeSearchURLIE (see the change design D4).
CHANNEL_SEARCH_FILTER = "EgIQAg%253D%253D"

_SEARCH_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "skip_download": True,
    "extract_flat": "in_playlist",
}


def _thumb(item):
    """Pick a mid-size thumbnail URL."""
    thumbs = []
    for t in item.get("thumbnails") or []:
        url = t.get("url") or ""
        if url.startswith("//"):
            url = "https:" + url  # protocol-relative (e.g. channel avatars)
        if url.startswith("http"):
            thumbs.append({"url": url, "width": t.get("width")})
    # prefer an exact 320x180-ish entry, else the biggest
    if not thumbs:
        return None
    exact = [t for t in thumbs if (t.get("width") or 0) >= 320][:1]
    source = exact or thumbs
    # a direct thumbnail on i.ytimg is nicer than a storyboard
    for t in source:
        url = t.get("url") or ""
        if "i.ytimg.com" in url and "storyboard" not in url:
            return url
    return source[0].get("url")


def _sanitize(item):
    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "url": item.get("webpage_url") or ("https://www.youtube.com/watch?v=%s" % item.get("id")),
        "uploader": item.get("uploader") or item.get("channel"),
        "channel_id": item.get("channel_id"),
        "duration": item.get("duration"),
        "view_count": item.get("view_count"),
        "upload_date": item.get("upload_date"),
        "thumbnail": _thumb(item),
        "description": (item.get("description") or "")[:400],
    }


def _entries(info):
    """Return the inner entries of an extract_info result."""
    if not info:
        return []
    if info.get("_type") == "playlist":
        return info.get("entries") or []
    return [info]


def _looks_like_channel(item):
    """True when a flat search entry is a channel (not a video/playlist)."""
    channel_id = item.get("channel_id") or item.get("id") or ""
    if not str(channel_id).startswith("UC"):
        return False
    if not (item.get("title") or item.get("uploader")):
        return False
    url = item.get("channel_url") or item.get("webpage_url") or item.get("url") or ""
    return "/channel/" in url or item.get("ie_key") == "YoutubeTab"


def _sanitize_channel(item):
    return {
        "channel_id": item.get("channel_id") or item.get("id"),
        "name": item.get("title") or item.get("uploader") or item.get("channel"),
        "url": item.get("channel_url") or item.get("url"),
        "thumbnail": _thumb(item),
    }


def search_channels(query, limit=20):
    """Search YouTube for channels. Returns list of channel dicts.

    A channel dict is {"channel_id", "name", "url", "thumbnail"}; only entries
    that really are channels are kept (see _looks_like_channel). The extractor
    is capped at `limit` so it does not walk every page of the result list.
    """
    url = "https://www.youtube.com/results?search_query=%s&sp=%s" % (
        urllib.parse.quote_plus(query), CHANNEL_SEARCH_FILTER)
    try:
        with YoutubeDL(dict(_SEARCH_OPTS, playlistend=limit)) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception:
        return []
    out = []
    for item in _entries(info):
        if not item or not _looks_like_channel(item):
            continue
        channel = _sanitize_channel(item)
        if channel.get("channel_id") and channel.get("name"):
            out.append(channel)
        if len(out) >= limit:
            break
    return out


def search(query, limit=20):
    """Search videos. Only playable video entries are returned."""
    url = "ytsearch%d:%s" % (limit, query)
    with YoutubeDL(_SEARCH_OPTS) as ydl:
        info = ydl.extract_info(url, download=False)
    out = []
    for item in _entries(info):
        if not item or not _looks_like_video(item):
            continue
        s = _sanitize(item)
        if s.get("id") and s.get("title"):
            out.append(s)
    return out


def _looks_like_video(item):
    """True when a flat entry is a playable video (not a tab/playlist/channel).

    Guards the 'play a section' bug: a channel's tab entries (Videos, Shorts,
    Live) carry the *channel* id as their `id`, so without this check they end
    up as playable rows that fail with "This video is unavailable".
    """
    video_id = str(item.get("id") or "")
    if not _VIDEO_ID.match(video_id) or video_id == item.get("channel_id"):
        return False
    url = item.get("webpage_url") or item.get("url") or ""
    return "/watch?" in url or "youtu.be/" in url or item.get("ie_key") == "Youtube"


def channel_uploads(channel_id, limit=50, offset=0):
    """Uploads of a channel by id (UC...), newest first. Returns video dicts.

    Videos only: the channel's /videos tab is requested (no Shorts, Live or
    playlists) and entries that are not playable videos are dropped. The call is
    bounded to the [offset+1, offset+limit] window so a page renders quickly
    instead of walking every video the channel ever posted - the bare
    channel/<id> URL is a playlist of *tabs*, and extract_flat='in_playlist'
    resolves each of them (that alone made the channel page load forever).
    """
    first, last = offset + 1, offset + limit
    url = "https://www.youtube.com/channel/%s/videos" % channel_id
    opts = dict(_SEARCH_OPTS, extract_flat=True,
                playlist_items="%d-%d" % (first, last))
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception:
        return []
    out = []
    for item in _entries(info):
        if not item or not _looks_like_video(item):
            continue
        s = _sanitize(item)
        if not s.get("channel_id"):
            # Flat tab entries carry no channel_id; they belong to this channel.
            s["channel_id"] = channel_id
        if s.get("id") and s.get("title"):
            out.append(s)
        if len(out) >= limit:
            break
    return out

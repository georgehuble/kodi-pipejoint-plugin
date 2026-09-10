# -*- coding: utf-8 -*-
"""Entry point / router.

Actions (query params):
  (none)                        -> main menu (or play if video_id is given)
  new_search                    -> recent video queries + a New search... action
  search_input                  -> ask query, show video results
  results?q=...                 -> show video results for query (testable w/o dialog);
                                   the query is recorded in the search history
  remove_query?q=..             -> drop one query from the search history
  clear_queries                 -> clear the whole search history
  search_channels               -> ask query, show channel results (no history)
  subscriptions                 -> My subscriptions (stored channels)
  channel?channel_id=..[&name=] -> a Subscribe/Unsubscribe action row, a divider,
                                   then the newest uploads of the channel
  toggle_subscription?channel_id=..[&name=..]
                                -> subscribe/unsubscribe and reopen the channel
                                   page so the action row reflects the new state
  watch_history                 -> Watch history (watched videos, newest first)
  remove_history?video_id=..    -> drop one watch-history entry
  clear_history                 -> clear the whole watch history
  noop                          -> inert target (the channel page divider row)
  play?video_id=..[&quality=H][&resume=1]
                                -> resolve + setResolvedUrl; when quality (height,
                                   e.g. 720) is given the playback is capped at it,
                                   otherwise the add-on default quality applies.
                                   &resume=1 (a replay from Watch history) offers to
                                   continue from the saved position. Every play is
                                   recorded in the watch history, and the stop
                                   position is saved by the player monitor
  play_quality?video_id=..      -> resolve once, ask the user for a quality via a
                                   dialog, then start playback capped to the choice

Quality values are video heights (int) or 0/empty for Auto/Best (no cap).

Audio/subtitle defaults (add-on settings, applied on top of the resolved stream):
  default_audio (Auto|Original|<lang>)  -> for HLS, Audio is left to the player
                                           under Auto; otherwise the requested
                                           track (original language or an explicit
                                           tag) is asked for via the InputStream
                                           Adaptive original-audio-language property
                                           and, once playback starts, is selected
                                           deterministically among the player's own
                                           tracks (so a video that also exposes a
                                           dub or several codecs of one language
                                           still starts on the requested track)
  subtitles (Off|On)                    -> when On and the video exposes subtitle
                                           tracks, they are attached to the item
                                           so they appear in the player
Both defaults are additive preferences: they never block or interrupt playback.
"""

import os
import sys
import urllib.parse

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

# yt_dlp / catalog / resolver are vendored under resources/lib.
# Resolve the path relative to this file so we do not depend on
# xbmc.translatePath (removed in Kodi 21/Omega) or xbmcvfs.
_LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

import player_monitor  # noqa: E402
import resolver  # noqa: E402
import store  # noqa: E402
import ytlib  # noqa: E402

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")
HANDLE = int(sys.argv[1])
BASE = "plugin://%s/" % ADDON_ID

SETTING_DEFAULT_QUALITY = "default_quality"
SETTING_SHOW_HIGHER_RESOLUTIONS = "show_higher_resolutions"
AUTO_QUALITY = "Auto/Best"

# InputStream Adaptive stream-selection properties. A concrete quality is pinned
# with "fixed-res" so it does not start low and ramp up; Auto/Best asks for
# "adaptive" explicitly, so the behavior does not depend on the user's global
# InputStream Adaptive setting (see apply_stream_selection).
STREAM_SELECTION_PROP = "inputstream.adaptive.stream_selection_type"
CHOOSER_RESOLUTION_MAX_PROP = "inputstream.adaptive.chooser_resolution_max"
CHOOSER_BANDWIDTH_MAX_PROP = "inputstream.adaptive.chooser_bandwidth_max"
STREAM_SELECTION_ADAPTIVE = "adaptive"
STREAM_SELECTION_FIXED = "fixed-res"

SETTING_DEFAULT_AUDIO = "default_audio"
SETTING_SUBTITLES = "subtitles"
AUDIO_AUTO = "Auto"
AUDIO_ORIGINAL = "Original"
AUDIO_ORIGINAL_LANG_PROP = "inputstream.adaptive.original_audio_language"

SUBSCRIBE_LABEL = "Subscribe"
UNSUBSCRIBE_LABEL = "Unsubscribe"
SEPARATOR_LABEL = "-" * 16
MORE_LABEL = "More videos..."

SEARCH_INPUT_ACTION = "search_input"
NEW_SEARCH_LABEL = "New search..."
REMOVE_QUERY_LABEL = "Remove from search history"
CLEAR_QUERIES_LABEL = "Clear search history"

WATCH_HISTORY_ACTION = "watch_history"
WATCH_HISTORY_LABEL = "Watch history"
WATCH_HISTORY_EMPTY = "No watch history"
PLAY_FROM_START_LABEL = "Play from the beginning"
REMOVE_HISTORY_LABEL = "Remove from watch history"
CLEAR_HISTORY_LABEL = "Clear watch history"

#: A saved position this close to the end is not a resume point: replaying such
#: an entry starts from the beginning instead of forcing a resume.
RESUME_NEAR_END_SECONDS = 30

#: Videos rendered per channel page; the next page is one "More videos..." away
#: (the whole list of a big channel cannot be fetched in one go).
CHANNEL_PAGE_SIZE = 50

# Subscriptions and the two histories are stored in the add-on profile
# directory. The concrete path is resolved here and injected into the
# xbmc-free store, so the store module itself never touches Kodi APIs.
PROFILE_DIR = "special://profile/addon_data/%s/" % ADDON_ID

_STORE = None
_WATCH_STORE = None
_SEARCH_STORE = None


def log(message, level=xbmc.LOGINFO):
    xbmc.log("[%s] %s" % (ADDON_ID, message), level)


def _translate(path):
    """Resolve a Kodi special:// path to a real path (identity if unavailable)."""
    try:
        import xbmcvfs

        return xbmcvfs.translatePath(path)
    except Exception:  # noqa: BLE001
        pass
    try:
        return xbmc.translatePath(path)
    except Exception:  # noqa: BLE001
        return path


def data_dir():
    """Concrete add-on data directory, or None when it cannot be resolved.

    Kodi returns the add-on profile (special://profile/addon_data/<id>/) from
    getAddonInfo('profile'); it is translated to a real path. When neither the
    profile path nor a real translation is available (e.g. a bare shim without
    xbmcvfs) the store is disabled instead of guessing a directory on disk.
    """
    try:
        path = ADDON.getAddonInfo("profile")
    except Exception:  # noqa: BLE001
        path = None
    resolved = _translate(path or PROFILE_DIR)
    if not resolved or resolved.startswith("special://"):
        log("could not resolve the add-on data directory; local store disabled")
        return None
    return resolved


def get_store():
    """The subscription store backed by the add-on data directory, or None."""
    global _STORE
    if _STORE is None:
        directory = data_dir()
        if directory:
            _STORE = store.SubscriptionStore(directory)
            _STORE.ensure_directory()
            log("subscription store: %s" % _STORE.path)
    return _STORE


def get_watch_store():
    """The watch-history store backed by the add-on data directory, or None."""
    global _WATCH_STORE
    if _WATCH_STORE is None:
        directory = data_dir()
        if directory:
            _WATCH_STORE = store.WatchHistoryStore(directory)
            _WATCH_STORE.ensure_directory()
            log("watch-history store: %s" % _WATCH_STORE.path)
    return _WATCH_STORE


def get_search_store():
    """The search-history store backed by the add-on data directory, or None."""
    global _SEARCH_STORE
    if _SEARCH_STORE is None:
        directory = data_dir()
        if directory:
            _SEARCH_STORE = store.SearchHistoryStore(directory)
            _SEARCH_STORE.ensure_directory()
            log("search-history store: %s" % _SEARCH_STORE.path)
    return _SEARCH_STORE


def build_url(action=None, **kwargs):
    if action:
        kwargs["action"] = action
    return BASE + "?" + urllib.parse.urlencode(kwargs)


def end():
    xbmcplugin.endOfDirectory(HANDLE)


def add_folder(label, url, thumb=None):
    item = xbmcgui.ListItem(label)
    if thumb:
        item.setArt({"thumb": thumb})
    xbmcplugin.addDirectoryItem(HANDLE, url, item, isFolder=True)


def add_video(data, url=None, playable=True):
    item = xbmcgui.ListItem(data.get("title") or "")
    if data.get("thumbnail"):
        item.setArt({"thumb": data["thumbnail"]})
    item.setProperty("IsPlayable", "true" if playable else "false")
    tag = item.getVideoInfoTag()
    tag.setTitle(data.get("title") or "")
    tag.setPlot(data.get("description") or "")
    try:
        tag.setDuration(int(data.get("duration") or 0))
    except (TypeError, ValueError):
        pass
    target = url or build_url("play", video_id=data.get("id"))
    if data.get("id"):
        item.addContextMenuItems(
            [("Play with quality...", build_url("play_quality", video_id=data["id"]))],
            replaceItems=False,
        )
    xbmcplugin.addDirectoryItem(HANDLE, target, item, isFolder=not playable)


def add_separator():
    """Inert divider row; its target is the no-op action (nothing happens)."""
    item = xbmcgui.ListItem(SEPARATOR_LABEL)
    item.setProperty("IsPlayable", "false")
    xbmcplugin.addDirectoryItem(HANDLE, build_url("noop"), item, isFolder=False)


def subscription_row(channel_id, name=None):
    """Render the channel page's leading Subscribe/Unsubscribe toggle.

    The label is the opposite of the current membership so that activating it
    performs the expected change. Returns the current membership state.
    """
    db = get_store()
    subscribed = bool(db and channel_id and db.is_subscribed(channel_id))
    label = UNSUBSCRIBE_LABEL if subscribed else SUBSCRIBE_LABEL
    add_folder(label, build_url("toggle_subscription", channel_id=channel_id, name=name or ""))
    return subscribed


def show_main_menu():
    add_folder("Search videos", build_url("new_search"))
    add_folder("Search channels", build_url("search_channels"))
    add_folder(WATCH_HISTORY_LABEL, build_url(WATCH_HISTORY_ACTION))
    add_folder("My subscriptions", build_url("subscriptions"))
    end()


def ask_query():
    dialog = xbmcgui.Dialog()
    return dialog.input("YouTube search", type=xbmcgui.INPUT_ALPHANUM)


def show_search_prompt():
    query = ask_query()
    if query:
        show_results(query)


def record_search_query(query):
    """Remember a performed video search.

    Only video searches reach here (channel search has its own function), which
    is what the spec asks for.
    """
    db = get_search_store()
    if db is None or not query:
        return False
    db.record_query(query)
    return True


def show_results(query):
    """Video results for `query`, recorded in the search history."""
    log("searching: %s" % query)
    record_search_query(query)
    try:
        results = ytlib.search(query)
    except Exception as error:  # noqa: BLE001
        log("search failed: %s" % error, xbmc.LOGERROR)
        results = []
    if not results:
        xbmcgui.Dialog().notification(ADDON_ID, "No results", xbmcgui.NOTIFICATION_WARNING)
    for r in results:
        add_video(r)
    end()


def add_query_row(query):
    """A recent-query row; selecting it re-runs that video search.

    The context menu drops this single query or clears the whole history.
    """
    item = xbmcgui.ListItem(query)
    item.addContextMenuItems(
        [
            (REMOVE_QUERY_LABEL, build_url("remove_query", q=query)),
            (CLEAR_QUERIES_LABEL, build_url("clear_queries")),
        ],
        replaceItems=False,
    )
    xbmcplugin.addDirectoryItem(HANDLE, build_url("results", q=query), item, isFolder=True)


def show_search_history():
    """Video search entry: a New search... action, then the recent queries.

    The action stays pinned at the top so it remains reachable as the history
    grows; the queries below follow newest-first.
    """
    db = get_search_store()
    queries = db.list_queries() if db else []
    log("search history: %d" % len(queries))
    add_folder(NEW_SEARCH_LABEL, build_url(SEARCH_INPUT_ACTION))
    for query in queries:
        add_query_row(query)
    end()


def remove_search_query(query):
    """Drop one query from the search history and reopen the search flow."""
    db = get_search_store()
    if db:
        db.remove_query(query)
        log("search history: removed %r" % query)
    show_search_history()


def clear_search_history():
    """Clear the whole search history and reopen the (now empty) search flow."""
    db = get_search_store()
    if db:
        db.clear_queries()
        log("search history cleared")
    show_search_history()


def show_channel(channel_id, name=None, offset=0):
    """Channel page: subscribe/unsubscribe row, divider, then the videos.

    Only the channel's own videos are listed (no Shorts/Live/playlists), newest
    first, CHANNEL_PAGE_SIZE at a time; a trailing "More videos..." row opens
    the next page so the whole channel stays reachable.

    `name` is the channel display name to store on subscribe; when it is not
    known (e.g. a bare channel?channel_id=... call) it is taken from the
    uploads, which carry the channel name as their uploader.
    """
    log("channel uploads: %s (offset=%d)" % (channel_id, offset))
    try:
        uploads = ytlib.channel_uploads(channel_id, limit=CHANNEL_PAGE_SIZE, offset=offset)
    except Exception as error:  # noqa: BLE001
        log("channel failed: %s" % error, xbmc.LOGERROR)
        uploads = []
    if not name:
        name = _uploader_name(uploads) or channel_id
    subscription_row(channel_id, name)
    add_separator()
    for u in uploads:
        add_video(u)
    if len(uploads) >= CHANNEL_PAGE_SIZE:
        add_folder(
            MORE_LABEL,
            build_url(
                "channel", channel_id=channel_id, name=name or "", offset=offset + CHANNEL_PAGE_SIZE
            ),
        )
    end()


def _offset_param(value):
    """Non-negative channel page offset from a URL param (garbage -> 0)."""
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _flag(value):
    """True when a URL param means "on" ("1", "true", "yes", "on")."""
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


def _uploader_name(uploads):
    """Best-effort channel display name from a channel's uploads."""
    for upload in uploads:
        if upload.get("uploader"):
            return upload["uploader"]
    return None


def toggle_subscription(channel_id, name=None):
    """Subscribe/unsubscribe channel_id, then reopen the channel page.

    Reloading the page is what makes the action row reflect the new state.
    """
    db = get_store()
    if db is None or not channel_id:
        notify_error("Subscriptions unavailable")
    elif db.is_subscribed(channel_id):
        db.unsubscribe(channel_id)
        log("unsubscribed: %s" % channel_id)
    else:
        db.subscribe(channel_id, name)
        log("subscribed: %s (%s)" % (channel_id, name))
    show_channel(channel_id, name)


def show_subscriptions():
    """My subscriptions: stored channels, newest first; each opens its page."""
    db = get_store()
    channels = db.list() if db else []
    log("subscriptions: %d" % len(channels))
    if not channels:
        xbmcgui.Dialog().notification(ADDON_ID, "No subscriptions", xbmcgui.NOTIFICATION_WARNING)
    for channel in channels:
        add_folder(
            channel.get("name") or channel.get("channel_id"),
            build_url(
                "channel", channel_id=channel.get("channel_id"), name=channel.get("name") or ""
            ),
        )
    end()


def add_history_entry(entry):
    """A playable Watch-history row; activating it replays the video.

    The play action asks about resuming when the entry has a usable saved
    position (see ask_resume). The context menu offers a fresh start, dropping
    this entry, and clearing the whole history.
    """
    video_id = entry.get("video_id")
    item = xbmcgui.ListItem(entry.get("title") or video_id)
    if entry.get("thumbnail"):
        item.setArt({"thumb": entry["thumbnail"]})
    item.setProperty("IsPlayable", "true")
    tag = item.getVideoInfoTag()
    tag.setTitle(entry.get("title") or "")
    try:
        tag.setDuration(int(entry.get("duration") or 0))
    except (TypeError, ValueError):
        pass
    item.addContextMenuItems(
        [
            (PLAY_FROM_START_LABEL, build_url("play", video_id=video_id, resume="0")),
            (REMOVE_HISTORY_LABEL, build_url("remove_history", video_id=video_id)),
            (CLEAR_HISTORY_LABEL, build_url("clear_history")),
        ],
        replaceItems=False,
    )
    xbmcplugin.addDirectoryItem(
        HANDLE, build_url("play", video_id=video_id, resume="1"), item, isFolder=False
    )


def show_watch_history():
    """Watch history: watched videos newest first; activating one replays it."""
    db = get_watch_store()
    entries = db.list() if db else []
    log("watch history: %d" % len(entries))
    if not entries:
        xbmcgui.Dialog().notification(ADDON_ID, WATCH_HISTORY_EMPTY, xbmcgui.NOTIFICATION_WARNING)
    for entry in entries:
        add_history_entry(entry)
    end()


def remove_history(video_id):
    """Drop one entry from the watch history and reopen the section."""
    db = get_watch_store()
    if db:
        db.remove(video_id)
        log("watch history: removed %s" % video_id)
    show_watch_history()


def clear_watch_history():
    """Clear the watch history and reopen the (now empty) section."""
    db = get_watch_store()
    if db:
        db.clear()
        log("watch history cleared")
    show_watch_history()


def show_channel_search_prompt():
    query = ask_query()
    if query:
        show_channel_results(query)


def show_channel_results(query):
    log("searching channels: %s" % query)
    try:
        results = ytlib.search_channels(query)
    except Exception as error:  # noqa: BLE001
        log("channel search failed: %s" % error, xbmc.LOGERROR)
        results = []
    if not results:
        xbmcgui.Dialog().notification(ADDON_ID, "No channels found", xbmcgui.NOTIFICATION_WARNING)
    for channel in results:
        add_folder(
            channel.get("name") or channel.get("channel_id"),
            build_url(
                "channel", channel_id=channel.get("channel_id"), name=channel.get("name") or ""
            ),
            thumb=channel.get("thumbnail"),
        )
    end()


def _quality_to_height(value):
    """Turn a quality value (setting or URL param) into a cap height or None.

    Accepts the settings labels ("Auto/Best", "720p", ...) as well as plain
    integers ("0", "720").  '', '0', 'Auto/Best' and None all mean Auto/Best ->
    None. Garbage is treated as Auto/Best rather than raising.
    """
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text or text in ("0", "auto", "best", "auto/best", "autobest"):
        return None
    if text.endswith("p") and text[:-1].isdigit():
        text = text[:-1]
    try:
        height = int(text)
    except (TypeError, ValueError):
        return None
    return height or None


def default_quality_height():
    """Cap height from the add-on 'default quality' setting, or None for Auto/Best."""
    try:
        raw = ADDON.getSetting(SETTING_DEFAULT_QUALITY)
    except AttributeError:
        raw = None
    return _quality_to_height(raw)


def _get_setting(name, default):
    """Addon setting value, defaulting when unavailable (shim-friendly)."""
    try:
        value = ADDON.getSetting(name)
    except AttributeError:
        return default
    if value is None or str(value).strip() == "":
        return default
    return value


def audio_preference(info):
    """(mode, lang) resolved from the 'default audio' setting and video info.

    mode is 'auto' (leave the player's choice), 'original' (the video's
    original track language, None when it cannot be determined) or 'language'
    (an explicit language tag). For 'auto', lang is always None.
    """
    setting = _get_setting(SETTING_DEFAULT_AUDIO, AUDIO_AUTO)
    text = str(setting).strip()
    if text == AUDIO_AUTO:
        return "auto", None
    if text == AUDIO_ORIGINAL:
        return "original", resolver.original_audio_language(info)
    return "language", text


def subtitles_default():
    """True when the 'subtitles' setting is On."""
    setting = _get_setting(SETTING_SUBTITLES, "Off")
    return str(setting).strip().lower() == "on"


def show_higher_resolutions_enabled():
    """True when the quality list should include heights above 1080p."""
    return _flag(_get_setting(SETTING_SHOW_HIGHER_RESOLUTIONS, "Off"))


def audio_intent(info):
    """(isa_lang, target_lang) for a resolved video; each None when not applicable.

    Computed once so the InputStream Adaptive hint set before playback and the
    post-start selection share the same decision (no duplicated logic). Auto
    yields (None, None); Original yields the detected original language.
    `isa_lang` is the language to request via the InputStream Adaptive property:
    an explicit tag is only requested when the resolved video actually exposes
    it among its audio-only tracks (across ISO 639 code forms, so `ru` counts as
    exposed when the manifest spells it `rus`), otherwise the player's fallback
    is used. The value is handed over in the form the manifest/player uses, so
    the hint can match (see resolver.isa_audio_language). `target_lang` is the
    language to match against the player's own tracks after playback starts (see
    player_monitor.select_audio_track); it is independent of the advertised list
    and of the code form, so a region or code variant can still match.
    """
    mode, lang = audio_preference(info)
    target = resolver.target_audio_language(mode, lang)
    isa_lang = None
    if lang is not None and (
        mode != "language" or resolver.audio_language_supported(info, lang)
    ):
        isa_lang = resolver.isa_audio_language(lang)
    return isa_lang, target


def attach_subtitles(item, info):
    """Attach playable subtitles to the ListItem when defaults say On.

    The original language (matching the audio default) is preferred, so a
    Russian original does not end up with one of the auto-translated caption
    tracks; when the original language has no playable track the first
    available one is used. Failures are only logged: they must never prevent
    playback (spec). With the setting Off, or when no playable track exists,
    nothing is attached. Returns the list of attached URLs (empty when none).
    """
    if not subtitles_default():
        return []
    lang = resolver.original_audio_language(info)
    urls = resolver.playable_subtitle_urls(info, lang=lang)
    if not urls:
        urls = resolver.playable_subtitle_urls(info)
    if not urls:
        return []
    try:
        item.setSubtitles(urls)
    except Exception as error:  # noqa: BLE001
        log("could not attach subtitles: %s" % error, xbmc.LOGERROR)
        return []
    return urls


def notify_error(message):
    xbmcgui.Dialog().notification(ADDON_ID, message, xbmcgui.NOTIFICATION_ERROR)


def resume_position(entry):
    """The usable resume position of a watch-history entry, in seconds.

    None when the entry has no saved position, or the position sits at (or next
    to) the end of the video - such an entry replays from the beginning instead
    of forcing a resume.
    """
    if not entry:
        return None
    position = entry.get("position")
    if not position or position <= 0:
        return None
    duration = entry.get("duration")
    if duration and position >= duration - RESUME_NEAR_END_SECONDS:
        return None
    return position


def _clock(seconds):
    """A saved position as h:mm:ss / m:ss, for the resume prompt."""
    total = int(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return "%d:%02d:%02d" % (hours, minutes, secs)
    return "%d:%02d" % (minutes, secs)


def ask_resume(video_id):
    """Seconds to resume from, or None to start from the beginning.

    Never asks when the entry has no usable position, so replaying a finished
    (or never-paused) video simply starts it from the beginning.
    """
    db = get_watch_store()
    position = resume_position(db.find(video_id) if db else None)
    if not position:
        return None
    options = ["Resume from %s" % _clock(position), "Start from the beginning"]
    if xbmcgui.Dialog().select("Resume playback", options) != 0:
        log("resume declined for %s" % video_id)
        return None
    log("resuming %s from %ss" % (video_id, position))
    return position


def apply_resume(item, seconds):
    """Ask the player to start at `seconds`.

    The offset travels as the ListItem 'StartOffset' property. The exact
    mechanism is confirmed by the real-Kodi spike (change task 2.3); it lives in
    this single helper so adjusting it stays a one-place change.
    """
    if not seconds or seconds <= 0:
        return False
    item.setProperty("StartOffset", str(int(seconds)))
    return True


def record_watch(video_id, info):
    """Add/refresh video_id in the watch history (written when play starts).

    Recording happens before the item reaches the player, so the fact of having
    watched the video survives even when the stop position cannot be observed.
    Returns the store, or None when no history is available.
    """
    db = get_watch_store()
    if db is None or not video_id:
        return None
    db.record(
        video_id,
        title=info.get("title"),
        url=info.get("webpage_url") or info.get("url") or "",
        thumbnail=info.get("thumbnail"),
        duration=info.get("duration"),
    )
    log("watch history: recorded %s" % video_id)
    return db


def start_monitor(video_id, audio_target=None):
    """Keep observing the player after setResolvedUrl to save the stop position.

    Isolated in player_monitor so the logic stays testable: outside Kodi (or
    when xbmc exposes no player) this is a no-op and the router behaves exactly
    as it did before. When `audio_target` is given the monitor also switches to
    that audio track once playback has begun, best-effort (see
    player_monitor.select_audio_track). Returns the stored position in seconds,
    or None.
    """
    if not video_id:
        return None
    player = player_monitor.new_player()
    if player is None:
        return None
    return player_monitor.monitor_playback(
        get_watch_store(), video_id, player, log=log, audio_target=audio_target
    )


def apply_stream_selection(item, info, max_height=None):
    """Tell InputStream Adaptive which stream to pick for an HLS playback.

    A concrete height is pinned with the "fixed-res" selection type, so the
    stream is fixed for the whole playback instead of starting at the lowest
    rendition and ramping up (the NewPipe behavior). InputStream Adaptive only
    accepts a discrete set of caps and nothing below 480p, so a lower request
    falls back to a bandwidth ceiling: playback then still never exceeds the
    request, although it may adapt within it. Auto/Best asks for "adaptive"
    explicitly, so the behavior does not depend on the user's global
    InputStream Adaptive setting.
    """
    if not max_height:
        item.setProperty(STREAM_SELECTION_PROP, STREAM_SELECTION_ADAPTIVE)
        return
    label = resolver.isa_resolution_label(max_height)
    if label:
        item.setProperty(STREAM_SELECTION_PROP, STREAM_SELECTION_FIXED)
        item.setProperty(CHOOSER_RESOLUTION_MAX_PROP, label)
        return
    item.setProperty(STREAM_SELECTION_PROP, STREAM_SELECTION_ADAPTIVE)
    bandwidth = resolver.bandwidth_for_height(info, max_height)
    if bandwidth:
        item.setProperty(CHOOSER_BANDWIDTH_MAX_PROP, str(bandwidth))


def play_stream(kind, stream, headers, info, max_height=None, video_id=None, resume_offset=None):
    """Build the ListItem for a resolved stream and hand it to the player.

    For HLS, max_height is applied through the InputStream Adaptive
    stream-selection properties (see apply_stream_selection): a concrete height
    is fixed for the whole playback, Auto/Best stays adaptive. For a progressive
    stream the cap is already reflected in the chosen stream URL, so no property
    is set.

    Audio/subtitle defaults are applied on top of the resolved stream: for HLS
    the preferred audio language is requested through the InputStream Adaptive
    original-audio-language property *and* selected deterministically among the
    player's own tracks after playback starts (Auto or an unavailable track
    leaves the player's choice), and subtitles are attached to the item when the
    setting is On and the video exposes playable tracks. Neither ever blocks
    playback.

    The play is recorded in the watch history before the item is handed over,
    and the process then keeps observing the player so the stop position can be
    saved (see record_watch / start_monitor). An accepted `resume_offset` is put
    on the item so the player starts there instead of at the beginning.
    """
    item = xbmcgui.ListItem(path=stream)
    item.setContentLookup(False)
    audio_lang = None
    audio_target = None
    if kind == "hls":
        item.setMimeType(resolver.HLS_MIME)
        item.setProperty("inputstream", "inputstream.adaptive")
        encoded = resolver.encode_headers(headers)
        if encoded:
            item.setProperty("inputstream.adaptive.manifest_headers", encoded)
            item.setProperty("inputstream.adaptive.stream_headers", encoded)
        item.setProperty("inputstream.adaptive.manifest_type", "hls")
        apply_stream_selection(item, info, max_height)
        audio_lang, audio_target = audio_intent(info)
        if audio_lang:
            item.setProperty(AUDIO_ORIGINAL_LANG_PROP, audio_lang)
    subtitle_urls = attach_subtitles(item, info)

    tag = item.getVideoInfoTag()
    tag.setTitle(info.get("title") or "")
    tag.setPlot(info.get("description") or "")
    try:
        tag.setDuration(int(info.get("duration") or 0))
    except (TypeError, ValueError):
        pass
    if info.get("thumbnail"):
        item.setArt({"thumb": info["thumbnail"]})
    log(
        "playing %s stream%s (audio_lang=%s, audio_target=%s, subtitle_urls=%d)"
        % (
            kind,
            " capped at %sp" % max_height if max_height else " (Auto/Best)",
            audio_lang,
            audio_target,
            len(subtitle_urls),
        )
    )
    apply_resume(item, resume_offset)
    record_watch(video_id, info)
    xbmcplugin.setResolvedUrl(HANDLE, True, item)
    start_monitor(video_id, audio_target=audio_target)


def play_video(video_id, quality=None, resume=False):
    """Resolve and play video_id, capped per quality.

    quality may be an explicit height (int/str) for this playback; when None the
    add-on default quality setting is used (Auto/Best when that is unset).

    `resume` marks a replay from the watch history: when the stored entry has a
    usable saved position the user is offered to continue from it; declining, or
    having no usable position, starts from the beginning.
    """
    if quality is None:
        max_height = default_quality_height()
    else:
        max_height = _quality_to_height(quality)
    try:
        kind, stream, headers, info = resolver.resolve_video(video_id, max_height=max_height)
    except Exception as error:  # noqa: BLE001
        log("resolution failed: %s" % error, xbmc.LOGERROR)
        notify_error("Could not resolve video")
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return

    resume_offset = ask_resume(video_id) if resume else None
    play_stream(
        kind,
        stream,
        headers,
        info,
        max_height=max_height,
        video_id=video_id,
        resume_offset=resume_offset,
    )


def play_quality(video_id):
    """Resolve once, let the user pick a quality, then play capped to the choice.

    Options are Auto/Best plus every selectable height of the resolved video
    (heights above 1080p only when the user enabled them). Cancelling the dialog
    starts nothing.
    """
    try:
        kind, stream, headers, info = resolver.resolve_video(video_id)
    except Exception as error:  # noqa: BLE001
        log("resolution failed: %s" % error, xbmc.LOGERROR)
        notify_error("Could not resolve video")
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return

    heights = resolver.selectable_heights(info, show_higher_resolutions_enabled())
    options = [AUTO_QUALITY] + [resolver.height_label(h) for h in heights]
    picked = xbmcgui.Dialog().select("Play with quality", options)
    if picked is None or picked < 0:
        log("quality dialog cancelled")
        return

    if picked == 0:
        max_height = None
    else:
        max_height = heights[picked - 1]

    # For a progressive fallback the cap is applied by re-selecting the best
    # muxed format no taller than max_height (no second network resolve).
    if kind != "hls" and max_height:
        capped_stream, capped_headers = resolver.pick_progressive(info, max_height=max_height)
        if capped_stream is not None:
            kind, stream, headers = "progressive", capped_stream, capped_headers

    play_stream(kind, stream, headers, info, max_height=max_height, video_id=video_id)


def main():
    params = dict(urllib.parse.parse_qsl(sys.argv[2].lstrip("?")))
    action = params.get("action")
    log("action=%s params=%s" % (action, params))

    if not action:
        # Direct plugin://.../?video_id=ID calls play immediately
        # (ytdlpcast / TubeCast style) instead of opening the menu.
        if params.get("video_id"):
            play_video(params["video_id"])
        else:
            show_main_menu()
    elif action == "new_search":
        show_search_history()
    elif action == SEARCH_INPUT_ACTION:
        show_search_prompt()
    elif action == "results":
        show_results(params.get("q", ""))
    elif action == "remove_query":
        remove_search_query(params.get("q", ""))
    elif action == "clear_queries":
        clear_search_history()
    elif action == "search_channels":
        show_channel_search_prompt()
    elif action == "subscriptions":
        show_subscriptions()
    elif action == WATCH_HISTORY_ACTION:
        show_watch_history()
    elif action == "remove_history":
        remove_history(params.get("video_id", ""))
    elif action == "clear_history":
        clear_watch_history()
    elif action == "channel":
        show_channel(
            params.get("channel_id", ""),
            name=params.get("name"),
            offset=_offset_param(params.get("offset")),
        )
    elif action == "toggle_subscription":
        toggle_subscription(params.get("channel_id", ""), name=params.get("name"))
    elif action == "noop":
        end()
    elif action == "play":
        play_video(
            params.get("video_id", ""),
            quality=params.get("quality"),
            resume=_flag(params.get("resume")),
        )
    elif action == "play_quality":
        play_quality(params.get("video_id", ""))
    else:
        log("unknown action: %s" % action, xbmc.LOGERROR)
        show_main_menu()


if __name__ == "__main__":
    main()

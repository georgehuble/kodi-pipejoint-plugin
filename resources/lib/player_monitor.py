# -*- coding: utf-8 -*-
"""Player-observation seam, kept apart from the router and testable.

A Kodi add-on stops running as soon as it hands an item to the player, so the
stop position can only be captured when the add-on sticks around and observes
playback. This module owns that observation:

- `new_player()` / `wait_seconds()` are the only Kodi-touching parts; outside
  Kodi they degrade to None / a plain sleep, so the router keeps its previous
  behaviour when no player is available.
- `monitor_playback()` is pure logic against a player-like object
  (`isPlaying()` / `getTime()`), so a fake player drives it in shim tests. When
  an audio target language is given it also performs a one-shot, best-effort
  audio-track selection: thin adapters (`available_audio_tracks` /
  `set_audio_track`) read and switch streams, and the pure
  `resolver.pick_audio_track` decides which one.

The final position goes back to the watch-history store. When playback ends
without a readable position nothing is written: the entry keeps the fact of
having been watched (recorded when playback started) and no resume point.
"""

import time

import resolver

#: Sleep between two player polls.
POLL_SECONDS = 1.0

#: How many polls to wait for playback to actually begin. A player that never
#: starts must not keep the add-on process alive forever.
START_POLLS = 10

#: How many times to retry the audio switch right after playback begins. The
#: player may not list its audio streams on the very first playing poll; a few
#: retries settle it without ever blocking playback.
AUDIO_SELECTION_ATTEMPTS = 3


def _xbmc():
    """The xbmc module when it is importable (Kodi), else None."""
    try:
        import xbmc
    except ImportError:
        return None
    return xbmc


def new_player():
    """A Kodi player instance, or None when xbmc.Player is unavailable."""
    xbmc = _xbmc()
    factory = getattr(xbmc, "Player", None) if xbmc is not None else None
    if factory is None:
        return None
    try:
        return factory()
    except Exception:  # noqa: BLE001 - a missing player must never break playback
        return None


def wait_seconds(seconds):
    """Sleep `seconds`, waking early when Kodi asks the add-on to stop."""
    xbmc = _xbmc()
    factory = getattr(xbmc, "Monitor", None) if xbmc is not None else None
    if factory is not None:
        try:
            return factory().waitForAbort(seconds)
        except Exception:  # noqa: BLE001 - fall back to a plain sleep
            pass
    time.sleep(seconds)
    return False


def _playing(player):
    """True while the player reports playback; a broken player counts as stopped."""
    try:
        return bool(player.isPlaying())
    except Exception:  # noqa: BLE001
        return False


def _position(player):
    """The player's current time in seconds, or 0.0 when it cannot be read."""
    try:
        return float(player.getTime())
    except Exception:  # noqa: BLE001
        return 0.0


def _track_from_player(entry, index):
    """Normalise one player-reported audio stream into a track mapping.

    Kodi reports available audio streams as strings; a richer double (or a
    future API) may hand a mapping with language/name/codec. Both shapes are
    accepted so the selection logic stays independent of the concrete API.
    """
    if isinstance(entry, dict):
        return {
            "index": index,
            "language": entry.get("language"),
            "name": entry.get("name") or entry.get("title"),
            "codec": entry.get("codec"),
        }
    return {"index": index, "language": entry, "name": entry, "codec": None}


def available_audio_tracks(player):
    """Audio tracks the player reports, as normalised mappings (never raises).

    Thin adapter over the player API: an unavailable or failing call yields an
    empty list, which the caller treats as "nothing to select".
    """
    try:
        streams = player.getAvailableAudioStreams()
    except Exception:  # noqa: BLE001 - a missing API must not break playback
        return []
    if not streams:
        return []
    return [_track_from_player(entry, index) for index, entry in enumerate(streams)]


def set_audio_track(player, index):
    """Ask the player to switch to the audio stream at `index` (never raises)."""
    try:
        player.setAudioStream(index)
        return True
    except Exception:  # noqa: BLE001 - a failed switch must not break playback
        return False


def select_audio_track(player, target_lang, log=None):
    """Switch to the player track matching `target_lang`; returns its index or None.

    Best-effort and one-shot: reads the player's audio tracks, picks one with
    the pure `resolver.pick_audio_track` and switches to it. An unreadable track
    list, no match or a failing switch all leave playback untouched and return
    None. Logs the target, the available languages and the actual choice so a
    real-Kodi session can be diagnosed from kodi.log.
    """
    if not target_lang:
        return None
    tracks = available_audio_tracks(player)
    index = resolver.pick_audio_track(target_lang, tracks)
    languages = [track.get("language") for track in tracks]
    if index is None:
        if log:
            log("player monitor: no audio track for %r among %s" % (target_lang, languages))
        return None
    if not set_audio_track(player, index):
        if log:
            log(
                "player monitor: could not switch to audio track %d (%r)"
                % (index, tracks[index].get("language"))
            )
        return None
    if log:
        log(
            "player monitor: switched audio to %r (track %d of %s)"
            % (tracks[index].get("language"), index, languages)
        )
    return index


def monitor_playback(
    history, video_id, player, wait=None, start_polls=START_POLLS, log=None, audio_target=None
):
    """Observe `player` until playback stops, then save the final position.

    Returns the stored position in seconds, or None when nothing was saved -
    either playback never began within `start_polls`, or it ended without a
    readable position (fact-only: no resume point is written).

    When `audio_target` is given, the audio track is switched to it once
    playback has begun (see select_audio_track): best-effort, idempotent, and
    never able to interrupt playback.
    """
    wait = wait or wait_seconds
    polls = 0
    while not _playing(player):
        if polls >= start_polls:
            if log:
                log("player monitor: playback never started for %s" % video_id)
            return None
        polls += 1
        wait(POLL_SECONDS)

    attempts = 0
    audio_done = not audio_target
    while _playing(player):
        if not audio_done and attempts < AUDIO_SELECTION_ATTEMPTS:
            attempts += 1
            if select_audio_track(player, audio_target, log=log) is not None:
                audio_done = True
        wait(POLL_SECONDS)

    position = _position(player)
    if position <= 0:
        if log:
            log("player monitor: %s ended without a position" % video_id)
        return None
    if history is None or not history.set_position(video_id, position):
        return None
    if log:
        log("player monitor: %s stopped at %ss" % (video_id, position))
    return position


__all__ = [
    "POLL_SECONDS",
    "START_POLLS",
    "AUDIO_SELECTION_ATTEMPTS",
    "new_player",
    "wait_seconds",
    "available_audio_tracks",
    "set_audio_track",
    "select_audio_track",
    "monitor_playback",
]

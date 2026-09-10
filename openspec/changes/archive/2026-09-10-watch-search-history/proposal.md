## Why

PipeJoint stores channel subscriptions locally but forgets everything else between sessions: previously watched videos cannot be re-found or resumed, and repeated searches have to be typed again. NewPipe keeps both - a watch history with resume position and a lightweight search history - entirely on-device. This change adds those two local histories to match that behavior.

## What Changes

- Add on-device **watch history**: videos are recorded when playback starts; a saved position is stored when playback stops; replaying a watched video from history resumes from the saved position; rewatching moves the entry to the top without duplicates.
- Add a Watch history main-menu section: entries newest-first, each opening playback (from start, or with a resume prompt when a position is saved); context menu can remove one entry or clear the whole history.
- Add on-device **search history** embedded in video search (like Elementum): opening Search videos shows recent queries plus a New search... action; selecting a past query re-runs it; context menu removes one entry or clears all; history is capped (e.g. 20) and duplicate-free.
- Record search history only for the video search; channel search keeps no history in this version.

### Non-goals

- No channel-search history (videos only).
- No cloud sync, no clearing on a timer, no per-account separation (single local profile).
- Subscriptions/catalog already shipped in the `local-storage-subscriptions` change; this change only adds histories on the same local store.

## Capabilities

### New Capabilities

- `history/watch-history`: recording watched videos, storing a resume position, resuming playback, listing/removing entries and clearing the watch history, all stored locally without duplicates.
- `history/search-history`: recording video search queries locally, showing recent queries inside the video search flow, re-running them, removing one/all and capping the stored list.

### Modified Capabilities

None. Existing `playback/*`, `subscriptions` and `channel-search` capabilities are untouched.

## Impact

- New/expanded xbmc-free local store (JSON) reused from the subscriptions change - extended with watch-history and search-history collections (path-injected, desktop-testable).
- `default.py`: Watch history main-menu section and router actions; watch-recording hook in the play path; a player-monitor seam that observes playback to save the position on stop; Search videos gains the recent-query list + New search... flow.
- `tests/`: desktop tests for history store semantics (dedup, cap, ordering, resume position); shim tests for the new router actions and the monitor seam.
- No change to playback stream resolution or the quality/audio-subtitle defaults.

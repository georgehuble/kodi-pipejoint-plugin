## Context

See proposal.md - Why. Current state shaping the approach:

- The router [`default.py`](../../../default.py) starts playback through `xbmcplugin.setResolvedUrl` and the add-on process currently returns once the item is handed to the player; there is no service and no player observation.
- A local xbmc-free JSON store is introduced in the sibling `local-storage-subscriptions` change (subscriptions). History will share that same store style (path-injected JSON under `addon_data`), not a new persistence technology.
- `ytlib` search flow already exists (`Search videos` -> `show_search_prompt`/`show_results`).
- Specs in this change: `history/watch-history` and `history/search-history`.

## Goals / Non-Goals

**Goals:**
- Reuse the xbmc-free JSON store pattern: add watch-history and search-history collections with deterministic, desktop-testable semantics (dedup, order, cap, resume position).
- Keep the router the only Kodi-touching layer; keep the player-observation behaviour behind a narrow, shim-testable seam so logic stays deterministic.
- Deliver watch history with a saved resume position and search history embedded in the video search flow.

**Non-Goals:**
- No channel-search history, no cloud sync, no timed clearing, no multi-profile separation.

## Decisions

### D1. Extend the shared JSON store with history collections

Watch history and search history live in the same path-injected JSON store used for subscriptions, exposed as separate repositories/collections. Watch entry fields: `video_id`, `title`, `url/thumbnail` for display, `timestamp` (for ordering), and `position` (seconds, may be absent/0). Search entry fields: `query` and `timestamp`.

- Alternative: separate files per collection. Not needed; a single store file keeps reads/writes simple, though collections may be persisted in one JSON object and loaded together.

### D2. Deterministic ordering and dedup in the store layer

The pure store layer owns ordering/dedup/cap logic so it is fully desktop-testable:
- record(video): if `video_id` exists, remove old copy; insert at front; cap watch history (no cap needed beyond sensible bound, decide e.g. unbounded or 100; record in design if bounded).
- set_position / on_stop updates `position` of the top entry.
- search record(query): dedup + front-insert + cap at 20 (configurable constant).

### D3. Watch recording hook and player-monitor seam

Recording happens when a play action resolves (before/at `setResolvedUrl`). Because a Kodi add-on does not run while the player plays, capturing the stop position requires the add-on to keep observing the player after starting playback. This is isolated in a small module that, in Kodi, keeps a `xbmc.Player` instance alive and writes the final position back on stop/end (the "monitor seam"). Under shim tests the seam is faked (record start event, simulate stop with a position) so no real player is needed.

- Alternative: a background service add-on. Rejected - heavier and out of scope; per-playback observation matches the requested approach.
- Risk noted: keeping the process alive after `setResolvedUrl` must be verified on Kodi 21 with ISA/HLS; if it proves unreliable the fallback is to record only the fact of watching (position best-effort), which the specs permit for a near-end position.
- Verified on Kodi 21 with ISA/HLS (2026-09-10, end-to-end run): the add-on process does stay alive after `setResolvedUrl`, the poll loop observes playback, and the stop position reaches the store (`player monitor: <video_id> stopped at <N>s`). The fact-only fallback stays in the code as a safety net (a player that never starts, or ends without a readable position, writes nothing).

### D4. Resume flow

Replaying a history entry passes a resume request; when a saved position exists the router offers "Resume from ..." / "Start from the beginning", so resuming is always optional. A near-end position (within `RESUME_NEAR_END_SECONDS` of the video duration) is not treated as a resume point at all.

- Verified on Kodi 21 with ISA/HLS (2026-09-10): the offset travels as the ListItem `StartOffset` property and playback starts at the saved position. `apply_resume()` in `default.py` is the only place this mechanism lives, so switching to another mechanism (e.g. an ISA property) stays a one-place change.

### D5. Search-history UI inside video search

The video search entry renders a `New search...` action pinned at the top, followed by the recent-query list (newest-first) - the action stays reachable as the history grows. Selecting a query re-runs it; the context menu removes one query or clears all. Only video searches write history; the `channel`/channel-search actions do not.

## Risks / Trade-offs

- [Player observation after setResolvedUrl may not be reliable across Kodi/ISA] -> Verified in a spike during implementation; fallback (fact-only recording) keeps specs intact.
- [Writing history on every play adds disk writes and store load] -> Small JSON, writes on start/stop only; acceptable.
- [Sharing one store file couples subscriptions and history] -> Collections are independent within the store; a future split is a refactor, not a spec change.

## Migration Plan

- Greenfield: no existing history data; store created empty on first run.
- Rollback: removing the change leaves history files orphaned but harmless; playback path otherwise unchanged.

## Open Questions

- Watch-history cap: decided to keep it unbounded unless it grows; a bounded cap (e.g. 100) is a trivial constant change and does not alter specs.
- Exact resume mechanism on Kodi/ISA (resolved by spike; does not change specs).

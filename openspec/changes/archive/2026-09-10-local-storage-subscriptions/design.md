## Context

See proposal.md - Why. Current state shaping the approach:

- [`ytlib.py`](../../../resources/lib/ytlib.py) is xbmc-free: it already exposes `search()` (videos) and `channel_uploads(channel_id)` (newest uploads) over bundled yt-dlp; every function returns plain dicts.
- The router [`default.py`](../../../default.py) owns all UI (`xbmcplugin.addDirectoryItem`, `xbmcgui`). Playback quality/audio/subtitle defaults already live on top of the resolved stream.
- No persistence exists today; the add-on keeps no state between invocations.
- Specs in this change: `subscriptions` and `channel-search` (see delta specs under `specs/`).

## Goals / Non-Goals

**Goals:**
- Introduce a local, xbmc-free JSON persistence module that stores channel subscriptions by `channel_id` + name and is testable on the desktop with an injected directory.
- Reuse `ytlib.channel_uploads` for the channel page video list (no behavior change there).
- Add channel search with a dedicated router action; add My subscriptions; add Subscribe/Unsubscribe as an action row on the channel page.
- Keep every new pure-logic module free of `xbmc*` imports so it can be exercised in `tests/` without Kodi (matching the resolver/ytlib pattern).

**Non-Goals:**
- No watch/search history (separate change).
- No aggregated feed, playlists, avatars or network sync.

## Decisions

### D1. JSON store module, path-injected and xbmc-free

A new module (e.g. `resources/lib/store.py`) manages a small JSON file (subscriptions list). The caller supplies the directory; in Kodi the router resolves it to `special://profile/addon_data/plugin.video.pipejoint/` (via `xbmcaddon`/`xbmcvfs`) and passes the concrete path, so the module itself stays import-free of Kodi. Reads are tolerant of a missing/corrupt file (start empty, never crash on read).

- Alternative: SQLite. Rejected for this scope - the data is a small ordered list; JSON is simpler, human-inspectable and matches the requested "simple, rollback-able" direction.

### D2. Subscription identity = channel_id; name is display metadata

A subscription is keyed by `channel_id` (deduplication on subscribe) and stores the channel `name` for display. No avatar is persisted. `subscribe(channel_id, name)`, `unsubscribe(channel_id)`, `is_subscribed(channel_id)` and `list()` operate on this model; `list()` returns channels newest-first or in subscription order (decided: subscription order, newest added first is acceptable and simplest).

### D3. Channel page: action row + video list

The channel page (existing `channel` action) gains a first row that is the Subscribe/Unsubscribe toggle: it reads current membership and builds the opposite action. The divider is realised as ordering: an action item row, then an inert separator item, then the uploads (reusing `ytlib.channel_uploads`). Selecting Subscribe/Unsubscribe reloads/re-renders the page so the state is reflected.

- Alternative (toggle only in a context menu): rejected - the user explicitly wants a visible Subscribe/Unsubscribe row at the top of the channel page.

**Video list (owner decision after the Kodi 21 check).** The page lists only the channel's own videos, newest first, and only playable ones: `channel_uploads` requests the `/videos` tab (never the bare channel URL - that is a playlist of *tabs* whose entries are Videos/Shorts/Live sections, and they were showing up as playable rows that failed with "This video is unavailable"), keeps entries that look like real videos (11-char video id + watch url, `id != channel_id`) and returns a single `[offset+1, offset+limit]` window. The page renders `CHANNEL_PAGE_SIZE` (50) videos plus a trailing "More videos..." row opening the same channel at `offset+CHANNEL_PAGE_SIZE`, so the whole channel stays reachable page by page while a page load stays bounded - walking every upload of a big channel is what made the channel page load forever.

### D4. Channel search mechanism (spike-dependent)

`ytlib.search()` searches videos via `ytsearchN:`. Channel-only search is not guaranteed by a stock yt-dlp extractor; the implementation must first run a spike to find a working mechanism - either a search URL with the channel filter (`sp=EgIQAg%3D%3D`) parsed for channel entries, or an available extractor - then expose `ytlib.search_channels(query)` returning sanitized channel dicts (`channel_id`, `name`, plus optional `thumbnail` when available) and reuse the same `_sanitize`-style helper. The router action prompts for the query, renders channel rows (folder) whose target is the existing `channel` action.

**Spike result (resolved, 2026-09-10):** the bundled `YoutubeSearchURLIE` accepts a channel-filtered search URL - no extra extractor needed. Verified with the vendored yt-dlp on the desktop:

```
https://www.youtube.com/results?search_query=<query>&sp=EgIQAg%253D%253D
```

With `extract_flat: "in_playlist"` the result is a flat playlist whose entries are channels: `id`/`channel_id` = `UC...`, `title`/`uploader` = the channel name, `url`/`channel_url` = `https://www.youtube.com/channel/UC...`, `thumbnails` populated and `ie_key` = `YoutubeTab` (spike query "kurzgesagt" -> `UCsXVk37bltHxD1rDPwtNM8Q` "Kurzgesagt - In a Nutshell"). `ytlib.search_channels(query, limit=20)` therefore builds that URL, keeps only entries that look like channels (a `UC` id plus a `/channel/` url or the `YoutubeTab` key), sanitizes them to `{channel_id, name, url, thumbnail}` and caps the list at `limit`.

### D5. Router actions and main menu

New actions: `search_channels`, `subscriptions`; existing `channel` gains the subscribe toggle row; the main menu lists Search videos / Search channels / My subscriptions. Channel result rows and My subscriptions rows both open `channel?channel_id=...`. All labels are English.

## Risks / Trade-offs

- [yt-dlp channel-only search may be brittle/unavailable] -> Spike first (task before finalizing search_channels); fallback documented: reuse video search entries and filter rows whose entry is a channel when supported, otherwise keep channel search limited to what the spike proves.
- [Concurrent invocations writing the JSON store] -> Kodi invokes the router once per action; writes are short and idempotent (subscribe/unsubscribe). Low risk for this scale; a write-through (load-modify-save) with a simple retry/ignore on read error suffices.
- [Reload on subscribe to reflect state may flash the directory] -> Acceptable; alternative (context-menu-only) was rejected in D3.

## Migration Plan

- Greenfield persistence: on first run the store file does not exist and is created empty; no migration of old data (none exists).
- Rollback: removing the change leaves the store directory/file orphaned but harmless; no existing feature depends on it.

## Open Questions

- Exact yt-dlp channel-search mechanism: **resolved** - the channel-filtered search URL above (spike recorded under D4; does not change the specs).
- Whether search-channel results also show thumbnails: not required by specs; store only `channel_id`+name as decided, thumbnails (if trivially available) are display-only and not persisted.

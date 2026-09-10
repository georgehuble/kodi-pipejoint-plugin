## Why

PipeJoint (a NewPipe-style local client) currently has no way to remember channels: every session starts from a search. NewPipe's core idea is that subscriptions and their uploads live on the device, privately and without an account. This change adds the first local-data capability - channel subscriptions backed by a small on-disk store - together with the channel search needed to discover and fill them.

## What Changes

- Add a local, xbmc-free JSON store for add-on data (a plain directory path is injected so it can run under desktop tests without Kodi).
- Add channel subscriptions: a channel is identified by `channel_id` plus a human-readable name (no avatar, no network sync). Subscribing and unsubscribing toggles membership.
- Add a "My subscriptions" main-menu section listing stored channels; selecting one opens the channel page.
- Channel page gains, above the video list, a Subscribe/Unsubscribe action (state reflects current membership) followed by a divider, then the channel's uploads newest-first (existing uploads listing reused).
- Add channel search: a "Search channels" main-menu entry whose results are channel items; selecting a result opens the channel page where the user can subscribe.
- Main menu becomes: Search videos / Search channels / My subscriptions (watch history is a separate future change).

### Non-goals

- No aggregated "feed of latest uploads across subscriptions" (NewPipe Feed) in this version.
- No watch/search history here (separate change `watch-search-history`).
- No channel avatars or channel metadata sync; only `channel_id` + name are stored.
- No playlists or account/cloud features.

## Capabilities

### New Capabilities

- `subscriptions`: local storage of channels the user follows (add/remove/list by channel_id+name) and the My subscriptions section plus the subscribe/unsubscribe action on a channel page.
- `channel-search`: searching YouTube for channels, rendering channel result items and opening a channel page from a result.

### Modified Capabilities

None. Existing `playback/*` capabilities are untouched.

## Impact

- New `resources/lib/` module(s): xbmc-free JSON store and subscriptions repository (path-injected, desktop-testable).
- `resources/lib/ytlib.py` (or a sibling catalog module): add a `search_channels(query)` capability via bundled yt-dlp (mechanism verified by a spike).
- `default.py`: new router actions for `channel_search`, `channel` page with subscribe/unsubscribe action item, and `subscriptions`; main-menu layout update.
- `tests/`: desktop tests for the storage/subscriptions repo on a temp dir; shim tests for the new router actions.
- No change to the playback/resolver paths.

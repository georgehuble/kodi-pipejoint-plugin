## 1. Local JSON store module (xbmc-free)

- [x] 1.1 Add an xbmc-free store module (e.g. `resources/lib/store.py`) that loads/saves a subscriptions list from a caller-supplied directory; verify with a desktop test using a temp dir that a missing file starts empty and a corrupt file does not crash (returns empty)
- [x] 1.2 Implement `subscribe(channel_id, name)`, `unsubscribe(channel_id)`, `is_subscribed(channel_id)`, `list()` on the store/repository with deduplication by `channel_id`; verify with desktop tests (subscribe twice -> one entry; unsubscribe removes it; list returns stored channels)

## 2. Wire the store path in the router

- [x] 2.1 In `default.py`, resolve the add-on data directory (`special://profile/addon_data/plugin.video.pipejoint/`) and construct the store with that path; verify the store module is constructed and its directory is created (shim test with an injected temp path)

## 3. Subscribe/Unsubscribe on the channel page

- [x] 3.1 Extend the `channel` action so the channel page renders a leading Subscribe/Unsubscribe row (opposite of current state), then an inert separator item, then the uploads list; verify in a shim test that the first row label matches the membership state and the videos follow
- [x] 3.2 Wire the Subscribe/Unsubscribe row to a router action that toggles membership by `channel_id`+name and re-opens the channel page; verify with a shim test that toggling updates the store and the action reflects the new state
- [x] 3.3 Fix the channel page video list hanging on large channels (found in the Kodi 21 check): `channel_uploads` now requests the channel's `/videos` tab with `extract_flat=True` and a hard cap - the bare `channel/<id>` URL is a playlist of *tabs*, and with `extract_flat='in_playlist'` yt-dlp resolved each tab, i.e. walked every video the channel ever posted. Verified live: 20 uploads in ~0.9s for `UCpVm7bg6pXKo1Pr6k5kxG9A` (National Geographic), which previously had not returned after 45s; guarded offline in `tests/test_channel_search_desktop.py`
- [x] 3.4 Videos only and a reachable full list (owner request from the Kodi 21 check): the channel page listed the channel's *tab* entries (Videos / Shorts / Live) as playable rows, so activating one tried to play `<channel_id>` and failed with "This video is unavailable". `channel_uploads` now keeps only real videos (`_looks_like_video`: 11-char video id, watch url, and never `id == channel_id`) and takes an `offset`, requesting just the `[offset+1, offset+limit]` window; the page renders `CHANNEL_PAGE_SIZE` (50) videos and a trailing "More videos..." row that opens the channel at `offset+50`, so every video stays reachable without fetching the whole list. Verified live on the channel from the log (`UC_hPYclmFCIENpMUhHpPY8FQ`... see kodi.log): 50 videos in 1.4s, next 50 in 1.8s, end of list at offset 200 in 2.9s, 0 non-video rows, and the first video resolves to an HLS stream in 2.2s. Shim test covers the "More videos..." row and the offset wiring; offline catalog test covers the section rejection and the paging window

## 4. My subscriptions section

- [x] 4.1 Add a `subscriptions` router action that lists subscribed channels and opens `channel?channel_id=...` on selection; verify with a shim test that only subscribed channels are listed and each row targets the channel action
- [x] 4.2 Add My subscriptions to the main menu (Search videos / Search channels / My subscriptions); verify the menu exposes all three entries

## 5. Channel search

- [x] 5.1 Run a spike on real Kodi/desktop to find a working yt-dlp mechanism for channel-only search (e.g. channel-filtered search URL) and record the working approach in design.md; verify the chosen approach returns channels with `channel_id`+name
- [x] 5.2 Add `ytlib.search_channels(query)` (xbmc-free) returning sanitized channel dicts; verify with the existing ytlib desktop test style (`python3 tests/test_ytlib_desktop.py` or an equivalent channel-search desktop check)
- [x] 5.3 Add a `search_channels` router action (prompt query, render channel rows -> `channel?channel_id=...`, inform when no results) and the Search channels main-menu entry; verify with a shim test (fake catalog) that rows carry the channel id and target the channel action

## 6. Integration verification

- [x] 6.1 Run the full desktop/shim set green: `python3 tests/test_resolver_quality.py && python3 tests/test_resolver_audio_subtitles.py && python3 tests/test_desktop.py && python3 tests/test_kodi_shim.py && python3 tests/test_kodi_shim_list.py && python3 tests/test_kodi_shim_quality.py` plus the new store/subscriptions/channel-search tests (`tests/test_store_desktop.py`, `tests/test_kodi_shim_subscriptions.py`, `tests/test_channel_search_desktop.py`, `tests/test_kodi_shim_channel_search.py`) - all green on 2026-09-10, including the live resolver/shim checks
- [x] 6.2 On a real Kodi 21 install verify: search a channel, open it, subscribe, see it under My subscriptions, open it again, unsubscribe, and confirm it disappears; record the result

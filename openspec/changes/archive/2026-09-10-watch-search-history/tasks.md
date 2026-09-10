## 1. History store collections (xbmc-free)

- [x] 1.1 Extend the shared xbmc-free JSON store with a watch-history collection: `record(video_id, title, url/thumbnail, position=None)`, dedup by `video_id` (move to front), ordering by recency; verify with desktop tests on a temp dir (new add at top; rewatch moves to top without dup; persisted across reload)
- [x] 1.2 Add `set_position(video_id, position)` to update the stored position of an entry (top-matching video); verify with a desktop test that the saved position updates and persists
- [x] 1.3 Extend the store with a search-history collection: `record_query(query)` with dedup + front-insert + cap at 20 (drop oldest), `remove_query`, `clear_queries`, `list_queries`; verify with desktop tests (cap drops oldest; repeat moves to top; remove/clear work)

## 2. Watch recording + player-monitor seam

- [x] 2.1 Record a video in the watch history when a play action resolves (before handing the item to the player); verify with a shim test that starting play adds/updates the entry
- [x] 2.2 Add a player-monitor seam: a module that, after `setResolvedUrl`, observes the player and writes the final position via `set_position` on stop/end; verify the seam logic with a shim test (fake player: start, stop at a position -> position stored; end without position -> fact-only)
- [x] 2.3 Run a spike on real Kodi 21 with ISA/HLS to confirm the monitor seam reliably captures the stop position while the add-on process stays alive; record the result in design.md and adjust the seam if needed

## 3. Resume flow and Watch history UI

- [x] 3.1 Add a resume flow: replaying a history entry with a saved position starts playback from that position (or offers Resume from...), while a near-end position does not force resume; verify with a shim test that the resume request/offset is applied only when a valid position exists
- [x] 3.2 Add the Watch history main-menu section (router action) listing entries newest-first that opens playback on activation; verify with a shim test that the listing order and play targets are correct
- [x] 3.3 Add context-menu actions on history entries: remove one entry and clear the whole history; verify with a shim test that remove drops the entry and clear empties the section

## 4. Search-history UI inside video search

- [x] 4.1 Rework the video search entry flow so it shows recent queries (newest-first) with a New search... action pinned at the top (so it stays reachable as the list grows), and records each performed video search via `record_query`; verify with a shim test that opening search shows New search... first with the recent queries below, and performing a search records the query
- [x] 4.2 Selecting a past query re-runs that video search; context menu removes one query or clears all; verify with shim tests that re-select triggers the query and remove/clear update the list

## 5. Integration verification

- [x] 5.1 Run the full desktop/shim set green (existing resolver/shim tests plus the new history store and router tests)
- [x] 5.2 On a real Kodi 21 install verify the end-to-end flow: play a video -> appears in Watch history; stop partway -> replay offers resume; search a query -> appears in recent; repeat/remove/clear behave; record the result

## Context

See `proposal.md` - Why. Current state that shapes the approach:

- [`resources/lib/resolver.py`](../../../resources/lib/resolver.py) is deliberately xbmc-free: `pick_hls` returns the HLS **master** `manifest_url`, so InputStream Adaptive always receives the full adaptive ladder. `available_heights(info)`/`height_label(height)` already enumerate and label the heights yt-dlp exposes.
- [`default.py`](../../../default.py) is the only Kodi-touching layer. [`play_stream`](../../../default.py) currently caps playback with `inputstream.adaptive.max_resolution`.
- Runtime confirms the property is dead: the log shows `inputstream.adaptive` v21.5.22 starting at `854x480` (initial bandwidth ~1.27 Mbit/s) while `max allowed: 2560x1440` is the screen size, then ramping to the 1080p rendition. The official InputStream Adaptive wiki does not list `max_resolution` among Kodi 20/21 properties at all.
- The supported replacement is the stream-selection API: `inputstream.adaptive.stream_selection_type` (`adaptive`, `fixed-res`, `ask-quality`, `manual-osd`, `test`) plus per-type `chooser_*` properties.
- NewPipe's model (checked against `TeamNewPipe/NewPipe`): a resolution list built from available streams, "best" pinned on top, 1440p/2160p hidden behind a `show higher resolutions` option, and playback of one fixed stream - no adaptive ramp.
- Specs for this change: `playback/quality-selection` already exists at `openspec/specs/playback/quality-selection/spec.md`; this change revises its requirements, so the delta uses MODIFIED blocks (plus one ADDED requirement).

## Goals / Non-Goals

**Goals:**
- Make a chosen quality actually take effect and stay fixed for the whole playback (NewPipe-like), instead of ramping from the lowest rendition.
- Keep the xbmc-free core: all height/bandwidth mapping lives in `resolver` as pure helpers; `default.py` only translates the result into ListItem properties.
- Keep Auto/Best genuinely adaptive and uncapped.
- Encode the new behavior in the rewritten quality tests and add `ruff` + `mypy` so the change can be verified with zero errors.

**Non-Goals:**
- Replacing the HLS playback path with a hand-built single-rendition DASH/MPD stream (proposal variant C).
- Per-title quality persistence, playlists, or any download feature.
- Changing audio/subtitle defaults or the histories.
- Switching quality mid-playback from the Kodi OSD. InputStream Adaptive only exposes the individual renditions to Kodi's stream list in its `manual-osd` selection type - `Session.cpp` adds one stream per representation only when the selection mode is manual, otherwise it adds a single stream per adaptation set. With `adaptive`/`fixed-res` Kodi therefore sees one video stream and the OSD has nothing to choose, which the runtime log confirms (one video id plus two audio ids for the played video). Enabling `manual-osd` would trade away the deterministic Auto/Best behavior, and was explicitly declined; quality is chosen before playback (the default setting or "Play with quality...").

## Decisions

### D1. Replace `max_resolution` with the stream-selection API

`inputstream.adaptive.max_resolution` is not a Kodi 20/21 property and is silently ignored. A concrete choice is expressed as an InputStream Adaptive stream-selection type instead of a cap:

- **Concrete quality** -> `stream_selection_type = fixed-res` plus `chooser_resolution_max = <label>`. This fixes one resolution for the whole video (no ramp), which is the NewPipe behavior requested.
- **Auto/Best** -> `stream_selection_type = adaptive` and no chooser property. Adaptive is chosen explicitly rather than left unset, so Auto/Best is deterministic regardless of the user's global InputStream Adaptive setting.

- Alternative: leave `stream_selection_type` unset for Auto/Best. Rejected - playback would then depend on the user's global ISA setting, making the spec's "Auto/Best remains adaptive" non-deterministic.
- Trade-off: setting `stream_selection_type` makes the InputStream Adaptive settings window ineffective for this add-on (documented ISA caution), and mid-playback quality switching from the Kodi OSD is unavailable as a consequence. Accepted for determinism; a user-facing `manual-osd` toggle could relax it later, but was declined for this change (see Non-Goals).

### D2. Mapping a requested height to what InputStream Adaptive can express

`chooser_resolution_max` accepts only a discrete set (`480p, 640p, 720p, 1080p, 2K, 1440p, 4K`), and it is a *maximum*, so a mapping must never let playback exceed the request.

- If the requested height has a supported value **at or below** it, pick the largest such supported value (exact match when possible, e.g. 720p, 1080p).
- If the requested height is **below** the smallest supported value, a resolution cap cannot express it (nothing below 480p). Fall back to a **bandwidth ceiling**: `stream_selection_type = adaptive` with `chooser_bandwidth_max` set to the bitrate of the best rendition at or below the requested height (from the yt-dlp format's bitrate). Playback may not pin the resolution, but it never exceeds the requested quality, which is the contract the spec requires.

- Alternative: drop sub-480p entries from the list. Rejected - the request explicitly wants 144p/240p/360p available, as NewPipe shows them.
- Verified against ISA's own source (`src/CompSettings.h`, `RES_CONV_LIST`): the supported caps and their pixel sizes are `480p` 640x480, `640p` 960x640, `720p` 1280x720, `1080p` 1920x1080, `2K` 2048x1080, `1440p` 2560x1440, `4K` 3840x2160. The smallest fixable height is therefore 480; 360p/240p/144p always take the bandwidth-ceiling branch.

### D3. Quality list source and higher-resolution gating

`available_heights(info)` stays the single source of the list (unique heights carrying a video codec, descending), with Auto/Best prepended. A new pure helper filters heights above 1080p unless the `show_higher_resolutions` add-on setting is On, mirroring NewPipe's hidden 1440p/2160p. Labels stay `NNNp` via the existing `height_label`.

### D4. Keep the pure core in `resolver`, the ListItem glue in `default.py`

New pure, desktop-testable helpers in `resolver`:

- `isa_resolution_label(height)` - the InputStream Adaptive label for a cap (or `None` when the height has no supported value at or below it).
- `bandwidth_for_height(info, height)` - bitrate (bit/s) of the best video rendition at or below `height`, for the sub-480p fallback.
- `selectable_heights(info, show_higher_resolutions)` - the filtered, descending list for the dialog.

`default.py::play_stream` becomes the only place that turns a chosen height into `stream_selection_type`/`chooser_resolution_max`/`chooser_bandwidth_max`; `max_height` keeps flowing to the progressive fallback (`pick_progressive`) as today.

### D5. Tests and tooling

- `tests/test_kodi_shim_quality.py` is rewritten: it used to assert `inputstream.adaptive.max_resolution`, i.e. it locked in the broken mechanism. The new assertions target `stream_selection_type` and `chooser_*`.
- A shared shim, `tests/kodi_shim.py`, replaces the per-file copies of the xbmc stubs and the fake resolver. The fake *delegates* every pure helper to the real `resolver`, so the helpers under test stay the production ones and no helper logic is duplicated. `tests/test_kodi_shim_quality.py` and `tests/test_kodi_shim_list.py` are migrated onto it; the remaining shim tests keep their own stubs, and migrating them is a follow-up rather than part of this change.
- A repo-root `pyproject.toml` configures `ruff` and `mypy`. Both exclude the vendored `resources/lib/yt_dlp/` tree. `mypy` additionally excludes `tests/`, because the shim tests install fake modules into `sys.modules` (xbmc, resolver, ytlib) which static analysis cannot model without a stub package; `ruff` still lints the tests. `ruff check` and `mypy` must report zero errors.
- Pure resolver helpers get desktop coverage in the existing desktop-test style.

## Risks / Trade-offs

- [Sub-480p qualities cannot be pinned to an exact resolution] -> Bandwidth-ceiling fallback in adaptive mode; the spec states the "never exceed" contract rather than an exact-resolution one for that case.
- [`fixed-res` buffers on an unstable connection because it cannot drop quality] -> Same trade-off NewPipe accepts; documented, not worked around.
- [Overriding `stream_selection_type` disables the user's ISA global setting for this add-on] -> Explicit and deterministic by design; a user-facing toggle is a deferred follow-up.
- [MyPy against a Kodi add-on can flood with environment errors] -> Constrain to the project's own sources/tests, exclude vendored `yt_dlp`, and ignore missing `xbmc*` imports.
- [The exact ISA-supported label set could differ from the wiki] -> Verify against ISA 21.5.22 at implementation time; the fallback branch keeps playback correct either way.

## Migration Plan

- No stored-data migration. Existing `default_quality` values (`Auto/Best`, `NNNp`, plain numbers) stay valid; a new `show_higher_resolutions` setting is added with a safe default (Off).
- Rollback: revert the ListItem properties in `play_stream`; playback falls back to plain adaptive HLS, as before the change.

## Open Questions

- Confirm on a live Kodi 21 session that `fixed-res` with `chooser_resolution_max` produces a single fixed stream in the add-on log (the label mapping itself is now taken from ISA's own source).

## Why

Choosing a video quality does not actually work on current Kodi. The add-on caps playback through `inputstream.adaptive.max_resolution`, a property that no longer exists in InputStream Adaptive 21, so the "Default video quality" setting is silently ignored. Playback is therefore left entirely to adaptive switching (ABR): it starts at a low rendition and ramps up later. Runtime evidence from a real session (`inputstream.adaptive` v21.5.22) shows an initial bandwidth of ~1.27 Mbit/s, an opening pick of `854x480`, and a later download of the 1080p rendition - exactly the "starts blurry, sharpens after a while" behavior reported by users. NewPipe instead plays one chosen resolution for the whole video, which is what we want to match.

The capability's spec does exist at `openspec/specs/playback/quality-selection/spec.md`, but it describes the cap-based behavior that never took effect, so its requirements are revised here rather than added.

## What Changes

- Drive quality selection through the supported InputStream Adaptive stream-selection API instead of the dead `max_resolution` property: a concrete choice fixes the stream for the whole video (NewPipe-like, no ramp), while Auto/Best keeps adaptive switching.
- Build the quality list from the artwork's actual available renditions, ordered highest to lowest, with Auto/Best always first; keep NewPipe's convention of hiding 1440p/2160p unless higher resolutions are enabled.
- Give the quality vocabulary one canonical mapping shared by the add-on setting, the per-video URL value, and the InputStream Adaptive property value.
- Where InputStream Adaptive cannot express an exact height directly, resolve the closest supported equivalent and document the limitation rather than silently ignoring the choice.
- **BREAKING** (internal): playback no longer sets `inputstream.adaptive.max_resolution`; the existing quality tests that assert that property are rewritten.
- Add `ruff` and `mypy` as the project's linter and type checker, configured to exclude the vendored `yt_dlp` tree, and make both pass with zero errors; remove the duplicated test scaffolding that accumulated around the quality paths.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `playback/quality-selection`: qualities above 1080p are hidden unless higher resolutions are enabled; a selected concrete quality is fixed for the whole playback instead of merely capped, and playback never exceeds it; the default setting gains the same fixed semantics with an explicit per-video choice overriding it; a requested quality beyond what the video offers plays the closest available quality at or below it.

## Impact

- `resources/lib/resolver.py`: quality enumeration/labelling helpers and the mapping from a height to the value InputStream Adaptive accepts.
- `default.py`: `play_stream` / `play_video` / `play_quality` set stream-selection properties instead of `max_resolution`; the quality list gains the higher-resolution gating already used by NewPipe.
- `resources/settings.xml`: default-quality options aligned with the canonical vocabulary.
- `tests/`: `tests/test_kodi_shim_quality.py` rewritten (it currently asserts the dead property) and its duplicated fake-resolver scaffolding consolidated; desktop coverage for the new resolver helpers.
- Tooling: new `ruff`/`mypy` configuration at the repo root excluding `resources/lib/yt_dlp/`; both tools added to the workflow so the quality change can be verified with zero errors.

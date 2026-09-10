## Why

The add-on is currently released as "OuterTube" (`plugin.video.outertube`, v0.2.5, MIT) while the repository is still named after the long-abandoned `kodi-invidious-plugin`. The project is being rebranded to **PipeJoint** and prepared for its first public **beta** release under a free license, so all packaging, identity metadata, and external references must be renamed consistently.

## What Changes

- **BREAKING**: Add-on id changes `plugin.video.outertube` -> `plugin.video.pipejoint` (display name `PipeJoint`, provider `pipejoint`). All `plugin://plugin.video.outertube/...` URLs, log prefixes, `ADDON_ID` usages and Kodi install folder names follow the new id.
- Version resets to `0.0.1` (first public beta) in `addon.xml`.
- License changes from `MIT` to **GPL-3.0**: add a full `LICENSE` file (`Copyright (C) 2026 PipeJoint contributors`) and update `addon.xml`/README. The resolver's MIT-derived origin note (ytdlpcast) is preserved in the source header.
- `Makefile` builds `plugin.video.pipejoint-0.0.1.zip`; `FILES` list is aligned (licence file name).
- README, UI labels/context-menu strings and any new docs reference `PipeJoint`; all **new** content is authored in English.
- Repository folder is renamed `kodi-invidious-plugin` -> `kodi-pipejoint-plugin` (external git/filesystem step, tracked in tasks).

### Non-goals

- No behavior changes to playback, search, quality, or audio/subtitle defaults.
- The two in-player OSD items ("Switch audio track" / "Switch subtitles") are explicitly **out of scope** for this change and tracked later.
- Existing Russian-authored OpenSpec artifacts (the in-flight `add-video-quality-selection` change and archived ones) are intentionally **not** translated; the English-only rule applies to new content.

## Capabilities

### New Capabilities

- `package-identity`: how the add-on identifies itself to Kodi and to users (add-on id, display name, provider, version, license and source metadata) so that branding is consistent across packaging, logs, URLs and documentation.

### Modified Capabilities

None. Existing capabilities (`playback/quality-selection`, `playback/audio-subtitle-defaults`) do not change their behavioral requirements.

## Impact

- `addon.xml` — id, name, provider, version, license, source.
- `LICENSE` — new GPL-3.0 file (referenced by `addon.xml` and `Makefile`).
- `Makefile` — dist artifact name and file list.
- `default.py` — `ADDON_ID`/log prefix (id-driven; no behavior change).
- Test shims referencing `ADDON_ID = "plugin.video.outertube"`.
- README and zip artifacts in the workspace root (historical `plugin.video.outertube-0.2.x.zip` files are left as-is).

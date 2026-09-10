## Context

See proposal.md - Why. Current state that shapes the approach:

- The add-on id `plugin.video.outertube` is baked into [`addon.xml`](../../../../addon.xml), used at runtime in [`default.py`](../../../../default.py) (`ADDON_ID`, `BASE` url, log prefix) and hard-coded in the Kodi-shim tests (`ADDON_ID = "plugin.video.outertube"`).
- The repo folder is `kodi-invidious-plugin` (stale name; workspace root cannot be renamed from inside the tooling - it is an external git/filesystem step).
- `Makefile` derives the dist archive name from the `<addon id>` in `addon.xml`, so renaming the id automatically renames the archive; its `FILES` list already includes `LICENSE.txt`.
- No `LICENSE` file exists yet; manifest declares `MIT`. Resolver module keeps a MIT attribution to `ytdlpcast` in its header.
- OpenSpec artifacts in the repo are authored in Russian; the English-only rule applies to new content only.

## Goals / Non-Goals

**Goals:**
- Single source of truth for identity: rename the `<addon id>` in `addon.xml` and let everything derived (archive name, `ADDON_ID`) follow, so no duplicate constants diverge.
- Add GPL-3.0 licensing consistent with NewPipe lineage, preserving the MIT-derived attribution.
- Reset version to `0.0.1` (first public beta).
- Keep every non-planning edit id-consistent and English-authored.

**Non-Goals:**
- No behavior change to playback/search/quality/audio-subtitle logic.
- No OSD ("Switch audio track"/"Switch subtitles") work (tracked separately).
- Do not translate or rewrite existing Russian OpenSpec artifacts.

## Decisions

### D1. Derive the add-on id from `addon.xml`, not from code constants

`default.py` already reads `ADDON_ID = ADDON.getAddonInfo("id")`, so renaming the manifest id propagates to `BASE` URLs and log prefixes automatically. The shim tests hard-code the id; they will be updated to assert the new id value read from the manifest (single source of truth) rather than a duplicate literal.

- Alternative: keep a constant in code. Rejected: it invites divergence from the manifest.

### D2. Manifest identity and version

`addon.xml`: `id=plugin.video.pipejoint`, `name=PipeJoint`, `provider-name=pipejoint`, `version=0.0.1`, `license=gpl-3.0`, and a `source` metadata URL pointing at the project's future repository (value set once the repo host/name is known; recorded as an open question).

### D3. License file and relicensing

Add `LICENSE` with the full GPL-3.0 text and `Copyright (C) 2026 PipeJoint contributors`. Keep the MIT attribution to ytdlpcast in `resolver.py`'s header (MIT code can be redistributed under GPL-3.0; attribution is retained). Update `Makefile` `FILES` if the license filename chosen differs from `LICENSE.txt`.

### D4. English-only new content, archive naming

New proposal/design/specs/tasks/README/UI text are authored in English. The dist archive is `plugin.video.pipejoint-0.0.1.zip` (automatic via D1/Makefile). Historical `plugin.video.outertube-0.2.x.zip` files are left untouched.

## Risks / Trade-offs

- [Changing the add-on id orphans existing installs/config/thumbnails of the old `plugin.video.outertube`] → Acceptable for a pre-release rename; documented as breaking. Users install the new add-on fresh.
- [`license=gpl-3.0` string must match what Kodi/the repo tooling expects] → Use the conventional SPDX-style value Kodi recognizes; verify during implementation.
- [Workspace folder rename (`kodi-invidious-plugin` -> `kodi-pipejoint-plugin`) is external] → Tracked in tasks as a git/filesystem step to run from the parent directory; does not affect in-repo identity work.
- [MIT-derived resolver code under a GPL-3.0 add-on] → Lawful (MIT is permissive, compatible), attribution header preserved.

## Migration Plan

- Implementation order: manifest identity+version+license → Makefile/license file → runtime/shims → README. Everything id-consistent lands in one change.
- Rollback: revert `addon.xml` id/name/license and the `LICENSE` file; no storage or data migration involved (no user data is stored yet).

## Open Questions

- Repository `source` URL for `addon.xml`/README (host + path of `kodi-pipejoint-plugin`). Not blocking: picked when the repo exists.

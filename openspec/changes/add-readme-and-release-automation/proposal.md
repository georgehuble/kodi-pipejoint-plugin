## Why

PipeJoint is about to be published as a **beta** for Kodi users, but the project currently has no public-facing documentation and no release process. The README is a short developer note, and the version identity has already drifted: it claims `0.0.1` while [`addon.xml`](../../../addon.xml:4) says `0.0.4`, so a hand-built archive can silently disagree with the manifest Kodi reads. Users cannot learn what the add-on does, how to install it in Kodi, or that it is beta, and no published version is reproducible or traceable. This change gives the project a NewPipe-style README (English + Russian), a single source of truth for the version, and an automated tag-driven release that builds the installable zip and publishes it.

## What Changes

- Rewrite [`README.md`](../../../README.md) in a NewPipe-style layout: centered logo, shields.io badges (release / license / CI / Kodi version), table of contents, a prominent **beta warning**, screenshots section, feature list, Kodi installation instructions, settings/usage, releases link, donation section (BTC + ETH) and license section.
- Add a Russian translation at `doc/README.ru.md` and cross-links between both READMEs. This widens the existing English-only documentation rule: the README stays English-primary with a maintained Russian translation.
- Align the manifest with the released identity: set `version` in [`addon.xml`](../../../addon.xml:4) to `0.0.1` (matching [`package-identity`](../../../openspec/specs/package-identity/spec.md:11)) so the first public release is `v0.0.1`.
- Add GitHub Actions:
  - `ci.yml` on push/PR: run `ruff`, `mypy` and the desktop/shim test suite.
  - `release.yml` on a `v*` tag: run the same checks, **fail when the tag does not equal the manifest version**, build the zip, and create a GitHub Release with the zip attached.
- Build the release asset as `kodi-pipejoint-plugin_v<version>.zip` while keeping the archive's single top-level folder as the add-on id `plugin.video.pipejoint/` (Kodi requires the inner folder name, not the asset name).
- Extend the [`Makefile`](../../../Makefile:10): a `release` target that bumps the manifest, commits, tags and pushes (`--follow-tags`), and a `dist` target that produces the release asset name; keep `docs/` out of the packaged zip.
- Add `docs/screenshots/` (with `en/` and `ru/`) for README images, plus a documented place for the license badge/asset.

### Non-goals

- No branch-per-version: releases are identified by git tags, not version branches.
- No auto-generated release table in the README and no in-Kodi auto-update mechanism (no `repository.pipejoint` repo add-on); release visibility is badges + the GitHub Releases page.
- No add-on UI localization (`resources/language/`, `strings.po`, translated `settings.xml`); the two languages here are README documentation only.
- No change to playback, catalog, storage or resolver behavior.

## Capabilities

### New Capabilities

- `release-automation`: how a published version is produced and traced - a single version source of truth in `addon.xml`, a tag-driven release pipeline that validates tag/version agreement, the packaged archive identity (asset name and inner add-on folder), and the local build/release entry points.
- `documentation`: the user-facing README deliverable - required sections (beta warning, features, Kodi installation, releases, donation, license), the English-primary + Russian-translation structure and their cross-links, and where README images and license assets live.

### Modified Capabilities

- `package-identity`: the archive-naming requirement changes from `plugin.video.pipejoint-<version>.zip` to the release asset name `kodi-pipejoint-plugin_v<version>.zip` (inner folder unchanged), and the English-only documentation rule changes to English-primary with a maintained Russian README translation.

## Impact

- [`README.md`](../../../README.md) rewritten; new `doc/README.ru.md`; new `docs/screenshots/en/`, `docs/screenshots/ru/`, `docs/assets/`.
- New `.github/workflows/ci.yml` and `.github/workflows/release.yml`.
- [`Makefile`](../../../Makefile:10): `dist` produces the release asset name and excludes `docs/`; new `release` target.
- [`addon.xml`](../../../addon.xml:4): version `0.0.4` -> `0.0.1`.
- [`.gitignore`](../../../.gitignore:1): ignore build artifacts (e.g. `*.zip`).
- Spec deltas: new `release-automation` and `documentation` specs, modified `package-identity` spec.
- External prerequisites (not code): the repository must have a remote, an initial commit and a `master` branch before CI/releases can run; donation addresses and screenshot images must be supplied by the maintainer.

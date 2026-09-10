## Context

See [`proposal.md`](proposal.md) - Why. Current state that shapes the approach:

- [`addon.xml`](../../../addon.xml:4) declares version `0.0.4` and provider `georgehuble`; the [`package-identity`](../../../openspec/specs/package-identity/spec.md:11) spec already requires version `0.0.1`. The manifest drifted; this change realigns it rather than changing the identity.
- [`Makefile`](../../../Makefile:1) derives `ADDON_NAME` and `VERSION` by grepping `addon.xml`, has a `FILES` list, builds `$(ADDON_NAME)-$(VERSION).zip`, and keeps a `prepare_release` target that clones `xbmc/repo-plugins` (the official Kodi repository path). That target is unrelated to this change and stays as is.
- There is no `.github/`, no `doc/`, no `docs/`, and no `resources/language/`; the packaged `FILES` list contains `addon.xml LICENSE README.md resources default.py icon.png`.
- [`pyproject.toml`](../../../pyproject.toml:7) already defines ruff (excluding the vendored `yt_dlp`) and mypy (excluding `yt_dlp` and `tests/`). Tests are plain scripts run as `python3 tests/<name>.py`.
- The repository currently has no commits and no remote, so CI cannot run until a first commit is pushed. This is a prerequisite, not a code task.
- Specs for this change: new `release-automation` and `documentation`, modified `package-identity` (deltas under [`specs/`](specs/)).

## Goals / Non-Goals

**Goals:**

- One version source of truth (`addon.xml`), with the release tag mirroring it and the pipeline proving they agree.
- A tag-driven pipeline that produces the installable archive, names the release asset `kodi-pipejoint-plugin_v<version>.zip`, and keeps the archive's single top-level folder named `plugin.video.pipejoint`.
- Always-on checks on pushes and pull requests, independent of releases.
- A single local entry point that prepares a release (bump, commit, tag, push).
- A NewPipe-style README in English with a maintained Russian edition, and a documented home for screenshots and license assets that stays out of the packaged archive.

**Non-Goals:**

- No version branches and no branch-creation target in the build tooling (explicitly dropped from the original request in favour of tags).
- No auto-generated release table in the README and no in-Kodi auto-update mechanism.
- No add-on UI localization (`resources/language/`, `strings.po`, translated `settings.xml`).
- No changes to playback, catalog, storage, resolver or packaging content beyond the version string.

## Decisions

### D1. `addon.xml` is the version source of truth; the pipeline validates the tag

The manifest version is authoritative. The release pipeline reads the tag, strips the leading `v`, compares it to the manifest version, and fails before building when they differ.

- Alternative (tag injects the version into the manifest at build time): rejected. The artifact would then disagree with the committed source, and the repository would have two competing version sources.

### D2. Release trigger is a version tag; version branches are dropped

Pushing an annotated tag `v<version>` triggers the release. `make release VERSION=<version>` performs the local sequence: write the version into `addon.xml`, commit, create the annotated tag, and push the branch and tag together (`--follow-tags`).

- Alternative (version branch per release, as originally requested): rejected by explicit decision. Tags already make every version traceable and CI-friendly, and long-lived version branches would need ongoing maintenance.
- Tracking "all versions" therefore relies on the tags/releases list plus the release badge, not on branches.

### D3. Release asset name is independent of the archive layout

The asset is named `kodi-pipejoint-plugin_v<version>.zip`; inside, the single top-level folder remains the add-on id `plugin.video.pipejoint`. Kodi validates the inner folder name, not the file name, so the two can differ safely.

The `dist` target keeps building a staging directory named after the add-on id and zips it, then renames the produced file to the release asset name. The archive layout is asserted in CI with `unzip -l` (exactly one top-level `plugin.video.pipejoint/` and an `addon.xml` inside).

### D4. Two small workflows instead of one conditional workflow

- `ci.yml`: on push (any branch) and pull requests - ruff, mypy, and the test suite. No publishing.
- `release.yml`: on tags matching `v*` - the same checks, then the tag/version validation, then build and publish.

Rationale: keeps checks running on ordinary work (the requested "CI functionality") while releases stay tag-only, and re-running the checks inside the release job means a tag cannot bypass them. Coupling the trigger to the default branch name is avoided so a rename of the branch does not silently disable CI.

- Alternative (single workflow with conditional jobs): rejected for clarity; the two triggers have different failure semantics.

### D5. README structure mirrors NewPipe, with features sourced from specs

Layout: centered logo, badge row (latest release, license, CI status, supported Kodi version), language switch, table of contents, a prominent beta warning, screenshots, features, Kodi installation, settings/usage, supported services, contribution, releases link, donation, license.

The feature list is taken strictly from the existing specs (video search with recent queries, channel search, local subscriptions, watch and search history, resume position, video quality selection, audio/subtitle defaults, local storage, InputStream Adaptive playback). The current README's mention of playlists is not backed by any spec, so it must not be presented as available.

### D6. English primary with a Russian translation under `doc/`

`README.md` stays the English primary edition; the Russian edition lives at `doc/README.ru.md`, mirroring NewPipe's `doc/README.<lang>.md` convention, with cross-links near the top of both files. This narrows the existing English-only rule in [`package-identity`](../../../openspec/specs/package-identity/spec.md:42) to "English-primary documentation with a maintained Russian README translation"; specs and UI text stay English.

### D7. Documentation assets live under `docs/` and stay out of the archive

Screenshots go to `docs/screenshots/en/` and `docs/screenshots/ru/`, referenced from the READMEs with relative paths. Optional images (license, donation QR codes) go to `docs/assets/`. Because these directories are not part of the `FILES` list in [`Makefile`](../../../Makefile:3), they are automatically excluded from the packaged add-on.

The license is presented as a shields.io badge by default; a raster license image in `docs/assets/` is optional and changes only the README markup.

### D8. Build artifacts are ignored by git

`*.zip` is added to [`.gitignore`](../../../.gitignore:1) so locally built archives are never committed; the released archive is produced by CI and attached to the release.

## Risks / Trade-offs

- [Downgrading the manifest from `0.0.4` to `0.0.1` with a Kodi install already holding `0.0.4`] -> Kodi will not offer a downgrade. Mitigation: no public release, tag or remote exists yet, so there are no real installs; if a development install exists, the README release notes tell the user to reinstall rather than update.
- [A file name that no longer matches the inner folder can look inconsistent] -> The inner folder stays the add-on id and is asserted in CI; the asset name is documented as the download name.
- [Tag and manifest can still be edited by hand out of order] -> `release.yml` validates before building and fails fast; `make release` is the recommended path and keeps them consistent.
- [The README could advertise unimplemented work, as the current one does with playlists] -> The `documentation` spec forbids listing unimplemented features as available, and a task explicitly reconciles the current README's roadmap claims.
- [The Russian edition can drift from the English one over time] -> The `documentation` spec requires the same sections in the same order; reviewers check both files together. Automated comparison is not attempted.
- [Screenshots can bloat the repository and the archive] -> They are kept outside the packaged `FILES` list; archival size remains a review concern rather than a build concern.
- [Releases are visible on GitHub only; Kodi gains no update notification] -> Accepted and documented; an in-Kodi repository add-on remains a non-goal.

## Migration Plan

1. Prerequisite (maintainer): create the remote, push an initial commit, and confirm the default branch.
2. Align the manifest: `addon.xml` version `0.0.4` -> `0.0.1`; run the test suite once locally.
3. Add `.github/workflows/ci.yml` and confirm checks run on the next push.
4. Extend the [`Makefile`](../../../Makefile:10) with `dist` (release asset name, add-on-id staging folder) and `release` (bump, commit, tag, push); build locally and verify the archive layout with `unzip -l`.
5. Rewrite `README.md` (EN) and add `doc/README.ru.md`; add `docs/screenshots/{en,ru}/` and any `docs/assets/` files; add `.gitignore` entry for `*.zip`.
6. Add `.github/workflows/release.yml`; create and push tag `v0.0.1`; confirm the release and its asset.
7. Rollback: delete the tag and GitHub Release, revert the file changes. There is no runtime state or user data involved.

## Open Questions

- Donation addresses: **resolved** - the maintainer supplied Bitcoin, Ethereum, Solana and Tron addresses, with one shared EVM address reused for BNB Chain and Polygon. The `documentation` spec requires the address set to be listed and a shared address to be labelled with each network it serves.
- The screenshot images themselves are supplied by the maintainer; the READMEs reference the agreed paths and are filled once the files exist.
- Whether the license is shown as a badge only or additionally as an image depends on an asset the maintainer may supply; either satisfies the spec.
- Whether a `.github/CONTRIBUTING.md` is created or the Contribution section links to the issue tracker is left to implementation.
- The pre-existing drift between `provider-name` in [`addon.xml`](../../../addon.xml:5) (`georgehuble`) and [`package-identity`](../../../openspec/specs/package-identity/spec.md:11) (`pipejoint`) is out of scope here and needs its own decision.

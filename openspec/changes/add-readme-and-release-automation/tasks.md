## 1. Repository prerequisite and version realignment

- [ ] 1.1 Create the GitHub remote, make the initial commit on the main branch and push it; verify `git remote -v` lists the origin and `git log --oneline -1` shows a commit on the default branch (required before any CI/release run)
- [x] 1.2 Set the `version` attribute in [`addon.xml`](../../../addon.xml:4) from `0.0.4` to `0.0.1`; verify `grep 'version=' addon.xml` reports `0.0.1` and note in the release notes that an existing `0.0.4` development install must be reinstalled, not updated, because Kodi does not downgrade
- [x] 1.3 Add `*.zip` to [`.gitignore`](../../../.gitignore:1); verify `git status --short` does not list a locally built archive

## 2. Build tooling in the Makefile

- [x] 2.1 Rework `dist` in [`Makefile`](../../../Makefile:10) to stage the `FILES` into a folder named `plugin.video.pipejoint/` and produce `kodi-pipejoint-plugin_v<version>.zip`; verify with `make dist && unzip -l kodi-pipejoint-plugin_v0.0.1.zip` that there is exactly one top-level folder `plugin.video.pipejoint/` containing `addon.xml`, and that no `docs/` entries appear
- [x] 2.2 Add a `release` target that requires `VERSION`, writes it into `addon.xml`, creates a commit, creates an annotated tag `v$(VERSION)` and pushes the branch with `--follow-tags`; verify the sequence without publishing by running `make -n release VERSION=0.0.2`
- [x] 2.3 Keep `clean` working for the new archive name; verify `make dist && make clean` leaves no `*.zip` in the working tree

## 3. Continuous integration workflow

- [x] 3.1 Add `.github/workflows/ci.yml` triggered on push and pull requests, running ruff, mypy and the desktop/shim test suite, with no publishing step; verify the referenced commands all pass locally (`ruff check .`, `mypy .`, and the full `python3 tests/*.py` set) and that the workflow file parses as valid YAML
- [x] 3.2 Confirm the CI test invocation matches the project's actual entry points (plain `python3 tests/<name>.py` scripts, excluding the vendored `yt_dlp` tree); verify by running the same command line the workflow uses and seeing it exit 0

## 4. Release workflow

- [x] 4.1 Add `.github/workflows/release.yml` triggered on tags matching `v*` that runs the same checks, then fails when the tag version does not equal the `addon.xml` version, then builds the archive and publishes a GitHub Release with the archive attached; verify the mismatch branch locally by simulating `TAG=v0.0.2` against a manifest at `0.0.1` and seeing the validation fail
- [x] 4.2 Verify the workflow grants the permissions needed to create a release and attach an asset, and that it does not run on ordinary branch pushes

## 5. English README

- [x] 5.1 Rewrite [`README.md`](../../../README.md) with the required sections in order: centered logo, badge row (latest release, license, CI status, supported Kodi version), language switch, table of contents, beta warning, screenshots, features, installation, settings/usage, supported services, contribution, releases link, donation, license; verify every section from the `documentation` spec is present
- [x] 5.2 Populate the feature list strictly from existing specs (video search with recent queries, channel search, local subscriptions, watch and search history, resume position, video quality selection, audio/subtitle defaults, local storage, InputStream Adaptive playback); verify no listed feature lacks a backing spec and remove the unsourced playlist claim from the current README
- [x] 5.3 Write the installation section covering Kodi install-from-zip from the releases page, the unknown-sources prerequisite, and the development install/build path; verify the steps match the actual archive produced by `make dist`
- [x] 5.4 Add the beta warning before the descriptive content, stating the add-on is a beta and bugs may be encountered; verify it renders as an emphasised warning above the description
- [x] 5.5 Add the donation section with the maintainer's addresses (Bitcoin, Ethereum, Solana, Tron) and label the shared EVM address with each network it serves (Ethereum, BNB Chain, Polygon); verify each address is present and the shared one is labelled per network
- [x] 5.6 Add the badge row and a link to the releases page; verify the badge URLs point at the `georgehuble/kodi-pipejoint-plugin` repository and the releases link resolves to the GitHub Releases page

## 6. Russian README and cross-links

- [x] 6.1 Add `doc/README.ru.md` mirroring the English sections in the same order; verify a section-by-section comparison shows no missing or reordered sections
- [x] 6.2 Add a language switch near the top of both files linking each edition to the other; verify both links resolve to the correct file

## 7. Documentation assets

- [x] 7.1 Create `docs/screenshots/en/` and `docs/screenshots/ru/`, add the maintainer-supplied screenshots (or keep the directories with a placeholder), and reference them from both READMEs; verify each referenced image path exists
- [x] 7.2 Decide the license presentation in the README (shields.io badge by default, or an image under `docs/assets/`), add any license/QR asset there if used, and verify `make dist` still excludes `docs/` from the archive

## 8. Integration verification

- [x] 8.1 Run `openspec validate add-readme-and-release-automation --strict` and verify it passes with the three spec deltas (`release-automation`, `documentation`, `package-identity`)
- [x] 8.2 Run the full test suite green (`python3 tests/test_desktop.py`, the `tests/test_kodi_shim*.py` set, and the remaining `tests/test_*_desktop.py` scripts) and record the result
- [x] 8.3 Run `make dist` and verify the archive name is `kodi-pipejoint-plugin_v0.0.1.zip` and its single top-level folder is `plugin.video.pipejoint` containing `addon.xml`
- [ ] 8.4 Perform the first release rehearsal: push tag `v0.0.1`, confirm `.github/workflows/release.yml` runs, the release is published with `kodi-pipejoint-plugin_v0.0.1.zip` attached, and that pushing a deliberately mismatched tag fails without publishing
- [ ] 8.5 On a real Kodi 21 install, install the released archive via install-from-zip and confirm the add-on appears and starts (manual check)

## 1. Manifest identity and version

- [x] 1.1 Update `addon.xml`: `id=plugin.video.pipejoint`, `name=PipeJoint`, `provider-name=pipejoint`, `version=0.0.1`, `license=gpl-3.0`, and confirm the `requires` imports remain unchanged; verify the file parses as valid XML (e.g. `python3 -c "import xml.dom.minidom,sys;xml.dom.minidom.parse('addon.xml')"`)
- [x] 1.2 Add the `source` metadata value (repo URL for `kodi-pipejoint-plugin`) to `addon.xml` once known, or leave the agreed placeholder; verify manifest still validates

## 2. License

- [x] 2.1 Add `LICENSE` with the full GPL-3.0 text and `Copyright (C) 2026 PipeJoint contributors`; verify the file exists and the first lines match the GPL-3.0 header and copyright line
- [x] 2.2 Align `Makefile` `FILES` with the chosen license filename (e.g. `LICENSE`/`LICENSE.txt`) and confirm the dist copy includes it; verify `make -n dist` lists the license file
- [x] 2.3 Confirm the MIT attribution to ytdlpcast in `resolver.py`'s header is preserved; verify by reading the header after the change

## 3. Runtime and test id consistency

- [x] 3.1 Update Kodi-shim tests that hard-code `ADDON_ID = "plugin.video.outertube"` to the new id (asserting from `addon.xml` where practical); verify `python3 tests/test_kodi_shim.py && python3 tests/test_kodi_shim_list.py && python3 tests/test_kodi_shim_quality.py && python3 tests/test_kodi_shim_audio_subtitles.py` all pass
- [x] 3.2 Search the repo for remaining `plugin.video.outertube` / `OuterTube` / `outertube` references in non-archived code, tests and new docs and update them to the new id/name; verify a repo-wide grep returns no stale hits outside archived/openspec-history and the historical zip files

## 4. README and packaging

- [x] 4.1 Update `README.md` branding (title, id, install paths, layout notes) to PipeJoint and add a beta/version note (0.0.1); verify the README no longer references OuterTube/`plugin.video.outertube` outside history notes
- [x] 4.2 Produce a dist archive via `make dist` and verify it is named `plugin.video.pipejoint-0.0.1.zip` and contains `addon.xml`, `LICENSE`, `README.md` and `resources`
- [x] 4.3 (External step) Rename the repository folder `kodi-invidious-plugin` -> `kodi-pipejoint-plugin` from its parent directory and confirm git history/status is preserved (run from the parent, e.g. `mv kodi-invidious-plugin kodi-pipejoint-plugin`), documenting that this is a filesystem/git step not an in-repo edit

## 5. Integration verification

- [x] 5.1 Run the full desktop/shim test set and the dist build, and confirm the whole add-on still works with the new id on a real Kodi 21 install (fresh install of `plugin.video.pipejoint`, basic search and play); record the result

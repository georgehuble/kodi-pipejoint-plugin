## 1. Tooling baseline (ruff + mypy)

- [x] 1.1 Add a repo-root `pyproject.toml` with `[tool.ruff]` and `[tool.mypy]` sections that exclude the vendored `resources/lib/yt_dlp/` tree and ignore missing `xbmc*` imports; verify `ruff check .` and `mypy .` start and report config (not config-error) output.
- [x] 1.2 Install `ruff` and `mypy` and pin the working versions; verify by running `ruff --version` and `mypy --version`. (Installed via `uv tool install`: ruff 0.16.7, mypy 2.3.1.)
- [x] 1.3 Make `ruff check .` report zero findings for `default.py`, the project's own `resources/lib/*` modules and `tests/`; verify by running it and confirming exit code 0.
- [x] 1.4 Make `mypy` report zero errors for the same scope; verify by running it and confirming `Success: no issues found`. (`tests/` is excluded by design - see design.md D5 - and `resources/lib/ytlib.py` needed one real fix.)

## 2. Pure resolver helpers (xbmc-free)

- [x] 2.1 Add `isa_resolution_label(height)` returning the largest InputStream Adaptive cap at or below `height`, or `None` when no supported value is low enough; verify with a desktop test covering an exact match, a round-down and a no-supported-value case.
- [x] 2.2 Add `bandwidth_for_height(info, height)` returning the bitrate (bit/s) of the best video rendition at or below `height`; verify with a desktop test over a fake `formats` ladder.
- [x] 2.3 Add `selectable_heights(info, show_higher_resolutions)` returning the descending list with heights above 1080p included only when the flag is true; verify with a desktop test for both modes and for a video exposing no concrete heights.
- [x] 2.4 Confirm existing `available_heights`/`height_label`/`pick_progressive` behavior is unchanged and `ruff`/`mypy` stay clean for `resolver.py`; verify by running the existing desktop test.

## 3. Router and settings

- [x] 3.1 In `play_stream`, replace `inputstream.adaptive.max_resolution` with the stream-selection properties (`stream_selection_type` plus `chooser_resolution_max`, or `chooser_bandwidth_max` for the sub-480p fallback), leaving Auto/Best adaptive and uncapped; verify the quality shim test asserts the new properties and no longer the old one.
- [x] 3.2 Add the `show_higher_resolutions` setting (default Off) to `resources/settings.xml` and read it in the router; verify the selection list excludes 1440p/2160p when Off and includes them when On.
- [x] 3.3 Base `play_quality` options on `selectable_heights` so the higher-resolution gating applies; verify the offered-options assertion in the shim test.
- [x] 3.4 Confirm `play_video`'s default-quality path and the progressive fallback still receive `max_height` (the cap is applied by rendition selection, not a ListItem property); verify the progressive shim scenario still passes.

## 4. Test cleanup and coverage

- [x] 4.1 Extract the fake-resolver/xbmc-stub block duplicated across the shim tests into one shared helper module (`tests/kodi_shim.py`) and refactor the shim tests that deal with quality onto it; verify every shim test still passes.
- [x] 4.2 Rewrite `tests/test_kodi_shim_quality.py` for the new behavior; verify `max_resolution` no longer appears anywhere under `tests/` except as the explicit legacy-absence assertion.
- [x] 4.3 Add desktop tests for the new resolver helpers in the existing desktop-test style; verify each runs standalone with `python3`.

## 5. Verification

- [x] 5.1 Run the full test suite (desktop + shim) and confirm all tests pass. (15/15 pass.)
- [x] 5.2 Run `ruff check .` and `mypy` and confirm zero findings with exit code 0.
- [ ] 5.3 On a live Kodi 21 session, play a video with a concrete default quality and confirm the add-on log shows the fixed stream starting at that resolution with no later up-switch; confirm the `fixed-res` selection matches the label mapping taken from ISA's own source.

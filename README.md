<div align="center">
  <img src="icon.png" alt="PipeJoint logo" width="140">
  <h1>PipeJoint</h1>
  <p>A privacy-friendly YouTube client for Kodi.</p>
</div>

<div align="center">

[![Latest release](https://img.shields.io/github/v/release/georgehuble/kodi-pipejoint-plugin?label=release&color=blue)](https://github.com/georgehuble/kodi-pipejoint-plugin/releases)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/License-GNU_GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0.en.html)
[![CI](https://img.shields.io/github/actions/workflow/status/georgehuble/kodi-pipejoint-plugin/ci.yml?label=CI)](https://github.com/georgehuble/kodi-pipejoint-plugin/actions/workflows/ci.yml)
[![Kodi](https://img.shields.io/badge/Kodi-20%2B-blue)](https://kodi.tv)

</div>

**English** | [Русский](doc/README.ru.md)

## Table of contents

- [Beta status](#beta-status)
- [About](#about)
- [Screenshots](#screenshots)
- [Features](#features)
- [Installation](#installation)
- [Settings and usage](#settings-and-usage)
- [Supported services](#supported-services)
- [Contributing](#contributing)
- [Releases](#releases)
- [Donation](#donation)
- [License](#license)

## Beta status

> [!WARNING]
> **PipeJoint is in beta.** It is used every day, but it is still under active
> development: **bugs and rough edges may be encountered**, and behaviour can change
> between releases. Please report anything that breaks in the
> [issue tracker](https://github.com/georgehuble/kodi-pipejoint-plugin/issues).

## About

PipeJoint is a privacy-friendly YouTube client for Kodi. It talks **directly to YouTube**
using a bundled [yt-dlp](https://github.com/yt-dlp/yt-dlp) engine - there is no Google
account and no third-party Invidious instance in the middle:

- Search, channel pages and playback go straight to YouTube.
- Subscriptions and histories stay **on your device**; nothing is synced anywhere.
- Playback is resolved to a progressive or adaptive (HLS/DASH) stream and handed to
  **InputStream Adaptive** (`inputstream.adaptive`).

Supported environment:

| | |
| --- | --- |
| Kodi | 20 "Nexus" and newer |
| Tested with | Kodi 21 "Omega" |
| Add-on id | `plugin.video.pipejoint` |
| Version | 0.0.1 (beta) |
| License | GPL-3.0-or-later |

## Screenshots

The add-on UI is in English. These screenshots were taken on Kodi 21 "Omega".

|  |  |  |
| --- | --- | --- |
| ![PipeJoint screenshot 1](docs/screenshots/en/2026-09-10_23-16-18.png) | ![PipeJoint screenshot 2](docs/screenshots/en/2026-09-10_23-16-45.png) | ![PipeJoint screenshot 3](docs/screenshots/en/2026-09-10_23-17-06.png) |
| ![PipeJoint screenshot 4](docs/screenshots/en/2026-09-10_23-17-32.png) | ![PipeJoint screenshot 5](docs/screenshots/en/2026-09-10_23-18-26.png) | ![PipeJoint screenshot 6](docs/screenshots/en/2026-09-10_23-26-11.png) |

## Features

Every feature below is implemented and covered by the project's specifications.

- **Video search** - search YouTube from Kodi and get playable results with thumbnails.
- **Recent queries** - the search flow keeps your recent video searches (newest first,
  no duplicates, capped at 20) and re-runs one with a single click. Individual queries
  can be removed and the whole list cleared. Channel searches are not recorded.
- **Channel search** - find channels by name and open a channel page straight from the
  results.
- **Channel pages** - a Subscribe/Unsubscribe action at the top, then the channel's
  newest uploads, 50 at a time with a *More videos...* row for the next page.
- **Local subscriptions** - subscribe from a channel page and find everything again under
  *My subscriptions*. Stored on the device: no account, no sync, no network needed to read.
- **Watch history** - every playback is recorded locally (newest first, no duplicates);
  a single entry can be removed or the whole history cleared.
- **Resume position** - the playback position is saved when you stop, and replaying a
  history entry offers to continue where you left off (or to play from the beginning).
- **Video quality selection** - pick Auto/Best or a concrete quality per video through the
  *Play with quality...* context menu; a concrete choice is held for the whole playback.
  Qualities above 1080p appear only when enabled in the settings.
- **Audio and subtitle defaults** - choose the default audio track (Auto, Original or a
  specific language) and turn subtitles on or off; both are applied to every playback.
- **On-device storage** - subscriptions and both histories live in the add-on's own data
  directory, without any account or network sync.
- **InputStream Adaptive playback** - progressive and adaptive (HLS/DASH) streams are
  resolved by the bundled yt-dlp engine and delivered through `inputstream.adaptive`.

## Installation

### From a released archive (recommended)

1. Download the archive from the [releases page](https://github.com/georgehuble/kodi-pipejoint-plugin/releases)
   - for the first release that is `kodi-pipejoint-plugin_v0.0.1.zip`. Do **not** unpack it.
2. In Kodi, allow installation from zip files: open **Settings -> System -> Add-ons** and
   turn on **Unknown sources** (accept the warning).
3. Open **Add-ons -> Install from zip file**, browse to the downloaded
   `kodi-pipejoint-plugin_v0.0.1.zip` and confirm.
4. PipeJoint is now available under **Add-ons -> Video add-ons**. Kodi installs the required
   `inputstream.adaptive` dependency from its own add-on repository.

> [!NOTE]
> **Reinstall rather than update.** If you already have a development install of this add-on
> (for example a hand-built `0.0.4`), install this release fresh instead of updating it: Kodi
> does not offer a downgrade, so a newer version already on disk would otherwise stay in place
> and keep running the old build.

### Development install

Install from a working copy - copy or clone the repository into Kodi's add-on directory and
restart Kodi:

```shell
git clone https://github.com/georgehuble/kodi-pipejoint-plugin.git plugin.video.pipejoint
# then copy/symlink it into Kodi's add-on directory, for example:
#   flatpak Kodi: ~/.var/app/tv.kodi.Kodi/data/addons
#   classic Kodi: ~/.kodi/addons
```

Or build the installable archive locally and install it in Kodi from zip:

```shell
make dist        # -> kodi-pipejoint-plugin_v0.0.1.zip
```

The archive unpacks to a single top-level folder named after the add-on id,
`plugin.video.pipejoint/`, which is what Kodi expects.

## Settings and usage

The add-on opens with this main menu:

| Entry | What it does |
| --- | --- |
| Search videos | Opens the search flow: a **New search...** action plus your recent queries, newest first. Selecting a query re-runs it; the context menu removes one query or clears the whole history. |
| Search channels | Searches channels by name. Opening a result shows that channel's page. |
| Watch history | Watched videos, newest first. Selecting one replays it and offers to resume from the saved position when there is one; the context menu plays from the beginning, removes the entry or clears the history. |
| My subscriptions | Subscribed channels, newest first. Opening one shows its channel page. |

### Settings

| Setting | Values | Default | Effect |
| --- | --- | --- | --- |
| Default video quality | Auto/Best, 144p, 240p, 360p, 480p, 720p, 1080p, 1440p, 2160p | 720p | Quality used when a video is played without choosing one for that video. |
| Show resolutions above 1080p | Off / On | Off | Adds 1440p and 2160p to the quality options. |
| Default audio | Auto, Original or a language tag | Original | Audio track requested when playback starts. |
| Subtitles | Off / On | Off | Attaches the video's subtitle tracks so they appear in the player. |

### Choosing a quality per video

Highlight a video, open its context menu and choose **Play with quality...**, then pick
Auto/Best or a concrete quality. A concrete choice is held for the whole playback (playback
does not start lower and later ramp up, and never exceeds it); Auto/Best leaves adaptive
switching in place with no cap.

The audio and subtitle defaults are additive preferences: they never block or interrupt
playback.

## Supported services

| Service | Status |
| --- | --- |
| YouTube | Supported - video search, channel search, channel pages and playback go straight to `youtube.com`. |

PipeJoint is YouTube-only. It reaches YouTube directly through its bundled yt-dlp engine, so
it does not depend on Invidious instances (many of which now restrict their API) and needs no
Google account.

## Contributing

Issues and pull requests are welcome in the
[issue tracker](https://github.com/georgehuble/kodi-pipejoint-plugin/issues). Please keep
changes small and in English - specifications, UI labels and documentation alike.

Behaviour changes start as an OpenSpec change under [`openspec/changes/`](openspec/changes);
the specifications in [`openspec/specs/`](openspec/specs) are the source of truth. Run the
same checks CI runs before opening a pull request:

```shell
ruff check .
mypy .
for test_script in tests/test_*.py; do python3 "$test_script"; done
```

```text
default.py                  plugin router (menus, search, channels, playback)
resources/lib/
  resolver.py               yt-dlp stream resolution (progressive/HLS), xbmc-free
  ytlib.py                  catalog: video and channel search, xbmc-free
  store.py                  local subscriptions and histories, xbmc-free
  player_monitor.py         watch-history resume position tracking
  settings.xml              add-on settings
  yt_dlp/                   vendored yt-dlp engine
tests/                      desktop + Kodi-shim tests (no Kodi needed to run them)
.github/workflows/          ci.yml (checks) and release.yml (tag-driven release)
openspec/                   specifications and in-flight changes
```

`resolver.py`, `ytlib.py` and `store.py` are deliberately free of `xbmc*` imports so they can
be exercised on a desktop.

## Releases

Every published version is a GitHub Release with the installable archive attached:
**[Releases page](https://github.com/georgehuble/kodi-pipejoint-plugin/releases)**. The
badges at the top of this document show the latest release and the current CI status.

Releases are cut from version tags (`v0.0.1`), and a tag always matches the version declared
in [`addon.xml`](addon.xml). A release whose tag and manifest disagree is never published.

## Donation

PipeJoint is free software developed in spare time. If it is useful to you, donations are
welcome.

| Network | Address |
| --- | --- |
| Bitcoin (BTC) | `bc1qejp32veu4de2rd7smup76dmsxrakss7vf2ws4s` |
| Ethereum | `0x9372380E235Db79D597b1C227056990403829fcA` |
| BNB Chain | `0x9372380E235Db79D597b1C227056990403829fcA` |
| Polygon | `0x9372380E235Db79D597b1C227056990403829fcA` |
| Solana (SOL) | `AmwjXAGMzLRB7qi6KPsMWo2X47FGumLfevCioqVG3yTm` |
| Tron (TRX) | `TgnudM17V9XvNmrzSdBZxapESgQyY63jaL` |

The Ethereum address is a shared EVM address: the same address receives on **Ethereum**,
**BNB Chain** and **Polygon**, and is listed once per network it serves. Send assets only on
the network shown next to the address.

## License
[![GPL-3.0-or-later](docs/assets/licence.png)](https://www.gnu.org/licenses/gpl-3.0.en.html)
PipeJoint is distributed under the **GNU General Public License v3.0 or later**
(GPL-3.0-or-later) - see [`LICENSE`](LICENSE). PipeJoint is derived from MIT-licensed code, and
that attribution is preserved in the relevant source headers.

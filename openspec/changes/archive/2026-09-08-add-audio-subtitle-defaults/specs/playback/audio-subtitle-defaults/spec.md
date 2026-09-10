## Purpose

Lets OuterTube users pick the audio track (Auto, Original or a specific language)
and turn subtitles on/off by default, mirroring NewPipe's per-video controls, and
ensures subtitle streams are actually delivered to the Kodi player.

## ADDED Requirements

### Requirement: Default audio track setting

The system SHALL provide an add-on setting for the default audio track. The setting
SHALL support Auto (leave the player's current behaviour unchanged), Original (the
video's original audio track when one is present) and explicit language tags (for
example `ru`, `en-US`). The system SHALL apply this default whenever the user starts
playback without choosing an audio track for that specific video.

#### Scenario: Original audio requested and available

- **WHEN** the default audio setting is Original and a video provides both an original
  track (e.g. Russian) and a generated/dubbed English track
- **THEN** playback starts with the original track selected

#### Scenario: Explicit language requested and available

- **WHEN** the default audio setting is a language such as `en-US` and the video
  provides an `en-US` track
- **THEN** playback starts with that language track selected

#### Scenario: Requested track not available

- **WHEN** the default audio setting names a track (Original or a language) that the
  video does not provide
- **THEN** playback still starts using the player's fallback track without an error

#### Scenario: Auto default

- **WHEN** the default audio setting is Auto
- **THEN** the player's own audio selection is left unchanged

### Requirement: Default subtitles setting

The system SHALL provide an add-on setting for subtitles with at least Off and On
states. When On, playback SHALL start with subtitles enabled; when Off, subtitles
SHALL NOT be enabled by default. The setting SHALL NOT prevent the user from toggling
subtitles manually during playback.

#### Scenario: Subtitles on by default

- **WHEN** the default subtitles setting is On and the video has subtitles
- **THEN** playback starts with subtitles shown

#### Scenario: Subtitles off by default

- **WHEN** the default subtitles setting is Off
- **THEN** playback starts without subtitles, and the user can still turn them on
  during playback

### Requirement: Subtitle streams delivered to the player

The system SHALL attach subtitle streams found during resolution to the playback
item, so that subtitle tracks are available to and selectable in the Kodi player.
The system SHALL use both manually authored subtitles and automatically generated
captions exposed by the resolved video. This is a fix: previously subtitles were
never handed to the player and therefore never appeared.

#### Scenario: Subtitles available from the resolved video

- **WHEN** a video is played and its resolved information exposes subtitle or caption
  tracks
- **THEN** those tracks are attached to the playback item and appear in the player's
  subtitle selector

#### Scenario: No subtitles available

- **WHEN** a video is played and the resolved information exposes no subtitle or
  caption tracks
- **THEN** playback continues normally with no subtitle tracks attached

### Requirement: Playback never blocked by audio or subtitle selection

The system SHALL treat audio and subtitle defaults as additive preferences applied on
top of an already-resolved stream. A failure to read a subtitle or audio track, or
their absence, SHALL NOT prevent the video from playing.

#### Scenario: Subtitle attachment failure does not block playback

- **WHEN** attaching subtitles fails for a video
- **THEN** the video still plays and the failure is only logged, with no error dialog

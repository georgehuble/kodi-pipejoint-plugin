# Audio & Subtitle Defaults Specification

## Purpose

Lets PipeJoint users pick the audio track (Auto, Original or a specific language)
and turn subtitles on/off by default, mirroring NewPipe's per-video controls, and
ensures subtitle streams are actually delivered to the Kodi player.

## Requirements

### Requirement: Default audio track setting

The system SHALL provide an add-on setting for the default audio track. The setting
SHALL support Auto (leave the player's current behaviour unchanged), Original (the
video's original audio track when one is present) and explicit language tags (for
example `ru`, `en-US`). The system SHALL apply this default whenever the user starts
playback without choosing an audio track for that specific video.

When a video exposes several audio renditions for the same set of languages (for
example an original and a dub, each available in more than one codec), the system
SHALL select the requested track deterministically instead of leaving the choice to
the player's own default: with Original it SHALL start on the original language and
SHALL NOT start on a dubbed track, and with an explicit language tag it SHALL start
on that language. The selection SHALL be based on the audio track's language and
role, not on its position in the stream list.

The system SHALL treat language tags as the same language across ISO 639 code forms:
a requested tag in one form (for example the two-letter `ru`) SHALL match a track the
player reports in another form (for example the three-letter `rus`), in addition to
the existing region-insensitive match (`ru` <-> `ru-RU`). The system SHALL apply this
equivalence both to the language requested from the player before playback and to the
track selected after playback starts, so that a two-letter original language still
selects a track the manifest exposes with a three-letter code.

The system SHALL treat the original and the default audio track as distinct: a track
marked as the default SHALL NOT be treated as the original one when an explicit
original track is present.

#### Scenario: Original audio requested and available

- **WHEN** the default audio setting is Original and a video provides both an original
  track (e.g. Russian) and a generated/dubbed English track
- **THEN** playback starts with the original track selected

#### Scenario: Original requested when the original track is offered in several codecs

- **WHEN** the default audio setting is Original and the video exposes the original
  language and a dubbed language, each in more than one audio rendition (for example
  AAC-LC and HE-AAC)
- **THEN** playback starts on a rendition of the original language and never on a
  dubbed rendition, regardless of the rendition order in the stream list

#### Scenario: A default-but-not-original track is not mistaken for the original

- **WHEN** the video marks a dubbed track as the default one and provides a separate
  original track
- **THEN** the Original setting still selects the original track, not the default dub

#### Scenario: Original language resolved in one ISO 639 form, track reported in another

- **WHEN** the default audio setting is Original, the resolved original language is the
  two-letter form (for example `ru`), and the player reports the original track with
  the three-letter form (for example `rus`) alongside a dubbed track (for example
  `en-US`) listed before it
- **THEN** playback starts on the original track and not on the first-listed dubbed
  track

#### Scenario: Explicit language resolved in one ISO 639 form, track reported in another

- **WHEN** the default audio setting is an explicit language such as `ru` and the video
  exposes that language with the three-letter code `rus`
- **THEN** playback starts with that language track selected

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

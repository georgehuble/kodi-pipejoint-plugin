## Purpose

Lets OuterTube users choose or cap the video quality of playback per video, mirroring
NewPipe's per-video quality control while keeping an Auto/Best default.

## ADDED Requirements

### Requirement: List available video qualities

The system SHALL present a list of quality options for a video, derived from the
qualities (heights) exposed by the resolved stream, ordered from highest to lowest and
always including an Auto/Best option. Options for concrete heights SHALL use standard
labels such as 2160p, 1440p, 1080p, 720p, 480p, 360p, 240p and 144p.

#### Scenario: Qualities derived from available formats

- **WHEN** a video resolves with stream formats exposing heights 2160, 1440, 1080, 720
- **THEN** the quality list offers Auto/Best, 2160p, 1440p, 1080p and 720p ordered from
  highest to lowest

#### Scenario: No concrete heights exposed

- **WHEN** a video resolves only with adaptive formats that expose no concrete heights
- **THEN** the quality list still offers Auto/Best so playback remains possible

### Requirement: Choose quality for a single playback

The system SHALL let the user select a quality for a video, choosing between Auto/Best
and any listed concrete quality, before that video starts playing. Selecting Auto/Best
MUST leave the stream uncapped (adaptive). Selecting a concrete quality MUST cap the
playback to that resolution.

#### Scenario: User picks a concrete quality

- **WHEN** the user selects 720p for a video whose stream supports up to 2160p
- **THEN** playback starts and does not exceed a resolution of 720p

#### Scenario: User picks Auto/Best

- **WHEN** the user selects Auto/Best for a video
- **THEN** playback starts without a resolution cap

#### Scenario: Requested quality exceeds what the video offers

- **WHEN** the user selects 2160p for a video whose highest available quality is 1080p
- **THEN** the video plays at its highest available quality without an error

### Requirement: Default video quality from settings

The system SHALL provide an add-on setting for the default video quality and SHALL apply
it whenever the user does not make a per-video choice. The default setting MUST support
Auto/Best plus the same concrete qualities as the per-video list.

#### Scenario: Default quality applied to playback

- **WHEN** the add-on default quality is 1080p and the user plays a video without
  choosing a per-video quality
- **THEN** playback caps at 1080p

#### Scenario: Default is Auto/Best

- **WHEN** the add-on default quality is Auto/Best and the user plays a video without
  choosing a per-video quality
- **THEN** playback is uncapped

### Requirement: Playback still resolves when quality list is unavailable

The system SHALL fall back to uncapped playback if quality enumeration fails for a video,
and MUST NOT prevent the video from playing.

#### Scenario: Enumeration failure does not block playback

- **WHEN** quality enumeration fails for a video being played
- **THEN** the video still plays using the default (uncapped) behavior and the user is
  not required to pick a quality

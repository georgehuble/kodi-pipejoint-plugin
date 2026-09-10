## MODIFIED Requirements

### Requirement: List available video qualities

The system SHALL present the quality options for a video, derived from the video resolutions
it actually exposes, ordered from highest to lowest and always including an Auto/Best option
first. Concrete options SHALL use standard labels such as 2160p, 1440p, 1080p, 720p, 480p,
360p, 240p and 144p. Qualities above 1080p (1440p, 2160p) SHALL be offered only when the
user has enabled higher resolutions, mirroring NewPipe's default of hiding them.

#### Scenario: Qualities derived from available formats

- **WHEN** a video resolves with stream formats exposing heights 2160, 1440, 1080 and 720,
  and the higher-resolutions option is disabled
- **THEN** the quality list offers Auto/Best, 1080p and 720p ordered from highest to lowest,
  and does not offer 1440p or 2160p

#### Scenario: Higher resolutions enabled

- **WHEN** the user enables higher resolutions for a video that exposes 2160 and 1440
- **THEN** the quality list additionally offers 1440p and 2160p in their highest-to-lowest
  position

#### Scenario: No concrete heights exposed

- **WHEN** a video resolves only with adaptive formats that expose no concrete heights
- **THEN** the quality list still offers Auto/Best so playback remains possible

### Requirement: Choose quality for a single playback

The system SHALL let the user select a quality for a video, choosing between Auto/Best and
any listed concrete quality, before that video starts playing. A selected concrete quality
SHALL be used for the whole playback: playback SHALL NOT start at a lower quality and later
switch to a higher one, and playback SHALL NOT exceed the selected quality. Selecting
Auto/Best MUST leave adaptive switching in place and impose no quality cap.

#### Scenario: User picks a concrete quality

- **WHEN** the user selects 720p for a video whose stream supports up to 2160p
- **THEN** playback begins at 720p or the closest available quality at or below 720p, stays
  there for the whole playback, and never exceeds 720p

#### Scenario: Quality below the smallest fixable resolution

- **WHEN** the user selects a quality lower than any resolution the platform can hold fixed
  (for example 144p)
- **THEN** playback still never exceeds the selected quality, even though it may adapt
  within that ceiling

#### Scenario: User picks Auto/Best

- **WHEN** the user selects Auto/Best for a video
- **THEN** playback starts without a resolution cap and remains free to switch quality
  adaptively

#### Scenario: Requested quality exceeds what the video offers

- **WHEN** the user selects 2160p for a video whose highest available quality is 1080p
- **THEN** the video plays at 1080p without an error

#### Scenario: Cancelling the choice starts nothing

- **WHEN** the user dismisses the quality selection without choosing
- **THEN** no playback is started

### Requirement: Default video quality from settings

The system SHALL provide an add-on setting for the default video quality and SHALL apply it
whenever the user does not make a per-video choice. The default setting MUST support
Auto/Best plus the same concrete qualities as the per-video list. An explicit per-video
choice SHALL override the default.

#### Scenario: Default quality applied to playback

- **WHEN** the add-on default quality is 1080p and the user plays a video without choosing a
  per-video quality
- **THEN** playback is fixed at 1080p or the closest available quality at or below 1080p, and
  never exceeds 1080p

#### Scenario: Default is Auto/Best

- **WHEN** the add-on default quality is Auto/Best and the user plays a video without choosing
  a per-video quality
- **THEN** playback is uncapped and remains adaptive

#### Scenario: A per-video choice overrides the default

- **WHEN** the add-on default quality is 1080p and the user explicitly chooses 360p for one
  video
- **THEN** that playback uses 360p, not the default

## ADDED Requirements

### Requirement: Handle a request below the available qualities

The system SHALL play the lowest available quality without exceeding the request when the
requested quality is lower than every quality the video exposes, and SHALL NOT fail the
playback.

#### Scenario: Requested quality is lower than anything available

- **WHEN** the user selects 144p for a video whose lowest available quality is 360p
- **THEN** the video plays at its lowest available quality (360p) without exceeding the
  request and without an error

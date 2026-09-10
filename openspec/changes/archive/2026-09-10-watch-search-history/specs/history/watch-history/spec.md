## Purpose

Defines how PipeJoint keeps a local record of the videos a user has watched - remembering them across sessions, storing a resume position, and letting the user revisit or resume them - without any account or network sync.

## ADDED Requirements

### Requirement: Record watched videos locally

The system SHALL record a video in the watch history when its playback starts. The history SHALL persist across sessions and SHALL NOT require an account or network access to read. A video SHALL appear at most once: re-watching an already-recorded video SHALL move it to the most recent position instead of duplicating it.

#### Scenario: Playback adds a video to history

- **WHEN** the user starts playing a video that is not in the history
- **THEN** the video is added to the top of the watch history

#### Scenario: Rewatching does not duplicate

- **WHEN** the user plays a video that is already in the history
- **THEN** the video still appears exactly once, moved to the most recent position

#### Scenario: History persists across sessions

- **WHEN** the add-on is closed and reopened
- **THEN** previously watched videos remain in the watch history

### Requirement: Store and resume a playback position

The system SHALL store the video's playback position when playback stops and SHALL offer to resume from that position when the user replays the video. A position that is at or near the very end SHALL NOT prevent normal (non-resumed) replay, and resuming SHALL remain optional.

#### Scenario: Position saved on stop

- **WHEN** the user stops playback of a video partway through
- **THEN** the saved position is stored with that history entry

#### Scenario: Replay offers resume from saved position

- **WHEN** the user replays a history entry that has a saved position
- **THEN** the user is offered the option to resume from that saved position rather than starting from the beginning

#### Scenario: Rewatching updates the stored position

- **WHEN** a video already in history is played again and stopped at a new position
- **THEN** its entry moves to the most recent position and the stored position is updated to the new one

### Requirement: Watch history section

The system SHALL expose a Watch history main-menu section listing recorded videos newest-first. Activating an entry SHALL start playback of that video (resumed or from the beginning per the resume flow). The section SHALL let the user remove an individual entry and clear the entire history.

#### Scenario: History lists newest first

- **WHEN** the user opens the Watch history section
- **THEN** recorded videos are listed with the most recently watched first

#### Scenario: Removing one entry

- **WHEN** the user chooses to remove a single history entry
- **THEN** that entry is removed and the other entries remain

#### Scenario: Clearing all history

- **WHEN** the user chooses to clear the history
- **THEN** all history entries are removed and the section shows an empty state

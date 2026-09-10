## MODIFIED Requirements

### Requirement: Branding consistency in user-facing and packaged content

The system SHALL use the `PipeJoint` name and `plugin.video.pipejoint` id consistently in user-facing text (UI labels and context-menu entries produced by the add-on), the README, and the packaged archive. Documentation SHALL be authored in English as the primary language, with a maintained Russian translation of the README. Specifications and UI text SHALL be written in English.

#### Scenario: Archive name matches the new identity

- **WHEN** a release archive is produced for version `0.0.1`
- **THEN** the release asset is named `kodi-pipejoint-plugin_v0.0.1.zip` and, when unpacked, contains a single top-level folder named `plugin.video.pipejoint`

#### Scenario: Documentation is English-primary with a Russian edition

- **WHEN** user-facing documentation is authored
- **THEN** it is written in English as the primary edition, and the README additionally has a maintained Russian translation that cross-links with the English edition

#### Scenario: New content is in English

- **WHEN** a specification or add-on UI label is authored
- **THEN** it is written in English

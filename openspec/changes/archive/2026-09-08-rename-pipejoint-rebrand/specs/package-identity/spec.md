## Purpose

Defines how the PipeJoint add-on identifies itself to Kodi and to users (add-on id, display name, provider, version, license and source metadata), so branding is consistent across packaging, logs, plugin URLs and documentation.

## ADDED Requirements

### Requirement: Add-on identity metadata

The system SHALL identify the add-on to Kodi with the add-on id `plugin.video.pipejoint`, display name `PipeJoint`, provider `pipejoint` and version `0.0.1`. The version SHALL be reported as a beta release.

#### Scenario: Kodi reads the manifest

- **WHEN** the add-on manifest is inspected by Kodi
- **THEN** the add-on id is `plugin.video.pipejoint`, the name is `PipeJoint`, the provider is `pipejoint` and the version is `0.0.1`

#### Scenario: Logs and plugin URLs use the new id

- **WHEN** the add-on logs a message or builds a `plugin://` URL
- **THEN** the log prefix and URL authority are based on `plugin.video.pipejoint`

### Requirement: Distribution license

The system SHALL be distributed under the GNU General Public License version 3 (GPL-3.0). The manifest SHALL declare the GPL-3.0 license and the repository SHALL include the full GPL-3.0 license text identifying the copyright holder as `PipeJoint contributors`. Attribution to MIT-licensed code that PipeJoint is derived from SHALL be preserved in the relevant source headers.

#### Scenario: License declared in the manifest

- **WHEN** the add-on manifest is inspected
- **THEN** the declared license is GPL-3.0

#### Scenario: License file present in the distribution

- **WHEN** the add-on is packaged
- **THEN** the distribution includes a license file containing the full GPL-3.0 text with the copyright line `Copyright (C) 2026 PipeJoint contributors`

#### Scenario: Derived-code attribution retained

- **WHEN** a source file carries an upstream MIT attribution
- **THEN** that attribution remains present and is not removed by the relicensing

### Requirement: Branding consistency in user-facing and packaged content

The system SHALL use the `PipeJoint` name and `plugin.video.pipejoint` id consistently in user-facing text (UI labels and context-menu entries produced by the add-on), the README, and the packaged archive filename. New documentation SHALL be authored in English.

#### Scenario: Archive name matches the new identity

- **WHEN** a distribution archive is produced
- **THEN** the archive is named after the new add-on id and version (e.g. `plugin.video.pipejoint-0.0.1.zip`)

#### Scenario: New content is in English

- **WHEN** new documentation, specs or UI text are authored
- **THEN** they are written in English

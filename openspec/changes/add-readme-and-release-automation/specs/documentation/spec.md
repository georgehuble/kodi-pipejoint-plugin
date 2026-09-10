## Purpose

Defines the user-facing README deliverable: which sections it must carry, how it presents the add-on's beta status, features, Kodi installation and support options, and how the English and Russian versions and their images are organised.

## ADDED Requirements

### Requirement: README is the primary user-facing document

The repository SHALL provide a README that describes the add-on, its purpose and its supported environment, so a new user can understand what the add-on is and whether it fits their setup without reading the source.

#### Scenario: Reader learns what the add-on is

- **WHEN** a reader opens the README
- **THEN** it states that the add-on is a privacy-friendly YouTube client for Kodi that resolves playback using a bundled yt-dlp engine and InputStream Adaptive, without a Google account or third-party Invidious instances

#### Scenario: Supported environment is stated

- **WHEN** a reader checks compatibility
- **THEN** the README states the supported Kodi version range and the Kodi version actually tested

### Requirement: Prominent beta warning

The README SHALL warn readers prominently that the add-on is a beta release and may contain bugs.

#### Scenario: Beta warning precedes the descriptive content

- **WHEN** a reader opens the README
- **THEN** an emphasised warning that the add-on is in beta, and that bugs may be encountered, appears before the description, feature list and installation sections

### Requirement: Feature list reflects implemented behavior

The README SHALL list the add-on's features, and every listed feature SHALL correspond to behavior already implemented and described by the project's specifications. Features that are planned but not implemented SHALL NOT be presented as available.

#### Scenario: Features match implemented capability

- **WHEN** a feature is listed as available in the README
- **THEN** the corresponding behavior exists in the add-on and is described by a specification

#### Scenario: Unimplemented work is not advertised

- **WHEN** a behavior is specified only as a future or planned change
- **THEN** the README does not present it as an available feature

### Requirement: Kodi installation instructions

The README SHALL explain how to install the add-on in Kodi, covering installation from the released archive and the requirement to allow installation from unknown sources, and SHALL describe the local development install path.

#### Scenario: Installing from the published archive

- **WHEN** a user follows the installation section for a published release
- **THEN** the instructions describe downloading the archive from the releases page and installing it in Kodi from a zip file

#### Scenario: Unknown sources prerequisite

- **WHEN** a user follows the installation instructions
- **THEN** the requirement to enable installation from unknown sources in Kodi is stated

#### Scenario: Development install documented

- **WHEN** a contributor follows the development instructions
- **THEN** the README explains how to install the add-on from a working copy and how to build the archive locally

### Requirement: Release visibility without extra automation

The README SHALL surface the current release status through repository badges and a link to the releases page, and SHALL NOT rely on a maintainer-updated version table.

#### Scenario: Badges show live status

- **WHEN** a reader opens the README
- **THEN** badges for the latest release, the license, the continuous integration status and the supported Kodi version are displayed

#### Scenario: Releases page is linked

- **WHEN** a reader wants to download or inspect published versions
- **THEN** the README links to the repository's releases page

### Requirement: Donation section

The README SHALL provide a donation section listing the maintainer's cryptocurrency donation addresses for every currency the project accepts.

#### Scenario: Donation addresses are listed

- **WHEN** a reader opens the donation section
- **THEN** a Bitcoin address, an Ethereum address, a Solana address and a Tron address are listed

#### Scenario: A shared address is presented per network

- **WHEN** a single address serves several EVM networks
- **THEN** the section identifies each network that shared address applies to

### Requirement: Screenshots and license assets

The README SHALL show screenshots of the add-on, stored under a documentation assets directory, and SHALL present the license either as a badge or as an image stored with those assets. Documentation assets SHALL NOT be included in the packaged add-on archive.

#### Scenario: Screenshots are displayed

- **WHEN** a reader opens the screenshots section
- **THEN** the screenshots are displayed and resolve to files under the documentation assets directory

#### Scenario: Assets stay out of the add-on package

- **WHEN** the add-on archive is built
- **THEN** the documentation assets directory is not part of the archive

### Requirement: English and Russian editions

The README SHALL be maintained in English as the primary edition with a Russian translation, and the two SHALL cross-link and cover the same sections.

#### Scenario: Reader can switch language

- **WHEN** a reader opens either edition
- **THEN** a link to the other language edition is available near the top of the document

#### Scenario: Sections stay in sync

- **WHEN** the Russian edition is read
- **THEN** it presents the same sections, in the same order, as the English edition

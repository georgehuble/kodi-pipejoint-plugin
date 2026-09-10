## Purpose

Defines how PipeJoint produces and traces published add-on versions: one version source of truth, a tag-driven pipeline that builds the installable Kodi archive, and the local entry point that prepares a release, so every published version is reproducible and agrees with the manifest Kodi reads.

## ADDED Requirements

### Requirement: Single version source of truth

The add-on manifest SHALL be the single source of truth for the released version. A release tag SHALL equal the manifest version, and a release SHALL NOT be published when the tag and the manifest disagree.

#### Scenario: Manifest carries the released version

- **WHEN** the add-on manifest is inspected at a release tag
- **THEN** its declared version equals the tag name without the leading `v`

#### Scenario: Mismatch blocks publication

- **WHEN** a version tag is pushed while the manifest declares a different version
- **THEN** the release pipeline fails and no release or asset is published

### Requirement: Tag-driven release pipeline

The system SHALL build and publish a release when a version tag is pushed. The published release SHALL be created for that tag and SHALL carry the installable add-on archive as a downloadable asset.

#### Scenario: Successful release from a tag

- **WHEN** a version tag is pushed and all automated checks pass
- **THEN** a release for that tag is published with the add-on archive attached as an asset

#### Scenario: Checks gate the release

- **WHEN** any automated check for the tagged revision fails
- **THEN** no release is published and no asset is attached

### Requirement: Release archive identity

The archive attached to a release SHALL be named `kodi-pipejoint-plugin_v<version>.zip`, and SHALL be installable in Kodi: it SHALL unpack to a single top-level folder named after the add-on id `plugin.video.pipejoint` that contains the add-on manifest.

#### Scenario: Release asset naming

- **WHEN** a release for version `0.0.1` is published
- **THEN** the attached archive is named `kodi-pipejoint-plugin_v0.0.1.zip`

#### Scenario: Archive installs in Kodi

- **WHEN** the released archive is unpacked
- **THEN** it contains exactly one top-level folder `plugin.video.pipejoint` and that folder contains `addon.xml`

### Requirement: Continuous integration on changes

The repository SHALL run its automated checks on pushes to the main branch and on pull requests, without publishing a release.

#### Scenario: Checks run without publishing

- **WHEN** a commit is pushed to the main branch or a pull request is opened
- **THEN** linting, type checking and the automated test suite are run and no release is created

### Requirement: Local release entry point

The build tooling SHALL provide a single local entry point that prepares a release for a given version: it updates the manifest version, records the change, and pushes the revision together with the version tag. It SHALL also be able to build the release archive locally under the same name the pipeline publishes.

#### Scenario: Preparing a release locally

- **WHEN** the maintainer runs the release entry point for version `0.0.2`
- **THEN** the manifest version becomes `0.0.2`, a commit for that revision is created, a version tag is created, and the revision and tag are pushed to the remote

#### Scenario: Local archive matches the published name

- **WHEN** the maintainer builds the archive locally
- **THEN** the resulting file is named `kodi-pipejoint-plugin_v<version>.zip`

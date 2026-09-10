# Channel Search Specification

## Purpose

Defines how PipeJoint lets the user find YouTube channels by query - a dedicated channel search whose results are channels, each openable to its channel page where the user can subscribe.

## Requirements

### Requirement: Search channels by query

The system SHALL provide a channel search that takes a text query and returns a list of channels matching that query. Each result SHALL expose the channel's `channel_id` and name.

#### Scenario: Query returns matching channels

- **WHEN** the user searches for a channel name
- **THEN** the results list contains channels matching the query, each carrying a channel id and name

#### Scenario: No channels match

- **WHEN** a channel search returns no matches
- **THEN** the user is informed that no channels were found

### Requirement: Channel search entry point in the main menu

The system SHALL expose a Search channels entry in the main menu, alongside Search videos and My subscriptions.

#### Scenario: Main menu offers channel search

- **WHEN** the user opens the main menu
- **THEN** it lists Search videos, Search channels and My subscriptions, and Search channels starts a channel search

### Requirement: Open a channel page from a search result

The system SHALL open the selected channel's page when the user activates a channel result, and that page SHALL behave like any other channel page (including the Subscribe/Unsubscribe action and uploads).

#### Scenario: Opening a channel from results

- **WHEN** the user activates a channel search result
- **THEN** the channel page opens with its Subscribe/Unsubscribe action and uploads

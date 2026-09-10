# Search History Specification

## Purpose

Defines how PipeJoint remembers video search queries on the device and surfaces them inside the video search flow, so users can quickly re-run past searches without retyping, while keeping the list bounded and easy to clear.

## Requirements

### Requirement: Record video search queries locally

The system SHALL record a query when a video search is performed. Queries SHALL persist across sessions and SHALL be stored without duplicates: repeating the same query moves it to the most recent position instead of adding a second copy. The stored list SHALL be capped at a fixed limit (e.g. 20), dropping the oldest query when exceeded. Channel searches SHALL NOT be recorded.

#### Scenario: A new video search is recorded

- **WHEN** the user performs a video search for a query not already in the history
- **THEN** that query is added to the most recent position of the search history

#### Scenario: Repeating a query does not duplicate

- **WHEN** the user searches for a query already in the history
- **THEN** the query appears once and moves to the most recent position

#### Scenario: History is bounded

- **WHEN** the number of stored queries exceeds the limit
- **THEN** the oldest query is removed so the list stays at or below the limit

#### Scenario: Channel searches are not recorded

- **WHEN** the user performs a channel search
- **THEN** no query is added to the video search history

### Requirement: Show recent queries inside the video search flow

The system SHALL show the recent video search queries when the user enters the video search flow, alongside an action to start a new search. Selecting a past query SHALL run that video search again.

#### Scenario: Recent queries and new-search action shown

- **WHEN** the user opens the video search flow
- **THEN** recent search queries are listed newest-first and a New search... action is available

#### Scenario: Selecting a past query re-runs the search

- **WHEN** the user selects a past query from the list
- **THEN** a video search for that query is performed

### Requirement: Remove search history entries

The system SHALL let the user remove an individual query and clear the entire search history from within the search flow.

#### Scenario: Removing one query

- **WHEN** the user chooses to remove a single stored query
- **THEN** that query is removed and the other queries remain

#### Scenario: Clearing all search history

- **WHEN** the user chooses to clear the search history
- **THEN** all stored queries are removed and the flow shows an empty history state

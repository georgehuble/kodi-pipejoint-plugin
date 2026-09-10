# Subscriptions Specification

## Purpose

Defines how PipeJoint stores and exposes the channels a user follows, entirely on the local device - listing, subscribing, unsubscribing and opening a channel from a subscription - without any account or network sync.

## Requirements

### Requirement: Store channel subscriptions locally

The system SHALL store channel subscriptions locally on the device so they persist across sessions. A subscription SHALL identify a channel by its `channel_id` and a human-readable channel name. The system SHALL NOT require an account or network access to read the stored list.

#### Scenario: Subscriptions persist across sessions

- **WHEN** the add-on is closed and reopened after channels have been subscribed
- **THEN** those channels are still present in the local subscription list

#### Scenario: A subscription is identified by channel id and name

- **WHEN** a channel is subscribed
- **THEN** it is stored with its `channel_id` and channel name, and no other data is required to list it

### Requirement: Subscribe to a channel

The system SHALL let the user subscribe to a channel from its channel page. After subscribing, the channel SHALL appear in the My subscriptions section. Subscribing the same channel again SHALL NOT create a duplicate.

#### Scenario: Subscribe from a channel page

- **WHEN** the user chooses Subscribe on a channel page that is not currently subscribed
- **THEN** the channel is added to the local subscriptions and the page action reflects the subscribed state

#### Scenario: Duplicate subscription has no effect

- **WHEN** the user subscribes to a channel that is already subscribed
- **THEN** no duplicate entry is created and the channel remains listed once

### Requirement: Unsubscribe from a channel

The system SHALL let the user unsubscribe from a channel from its channel page. After unsubscribing, the channel SHALL be removed from the My subscriptions section.

#### Scenario: Unsubscribe from a channel page

- **WHEN** the user chooses Unsubscribe on a subscribed channel page
- **THEN** the channel is removed from the local subscriptions and the page action reflects the unsubscribed state

### Requirement: My subscriptions section

The system SHALL provide a main-menu section that lists all subscribed channels. Selecting a subscribed channel SHALL open that channel's page.

#### Scenario: Listing subscribed channels

- **WHEN** the user opens the My subscriptions section
- **THEN** every subscribed channel is listed and channels that are not subscribed are not listed

#### Scenario: Opening a subscribed channel

- **WHEN** the user selects a subscribed channel from the section
- **THEN** the channel's page is shown

### Requirement: Channel page subscribe/unsubscribe action

The system SHALL place the Subscribe/Unsubscribe action at the top of the channel page, followed by a divider and then the channel's uploads. The action label and resulting state SHALL match the channel's current subscription status.

#### Scenario: Channel page shows the correct action for an unsubscribed channel

- **WHEN** an unsubscribed channel page is opened
- **THEN** the page shows a Subscribe action at the top and the channel's videos below it

#### Scenario: Channel page shows the correct action for a subscribed channel

- **WHEN** a subscribed channel page is opened
- **THEN** the page shows an Unsubscribe action at the top and the channel's videos below it

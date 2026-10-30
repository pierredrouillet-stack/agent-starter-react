# conversation-history Specification

## Purpose

Lets the user browse conversations with the LiveKit agent that were saved by the agent worker, so past voice and chat sessions can be re-read after they end. The frontend only reads saved conversations and never creates or changes them.

## Requirements

### Requirement: List saved conversations

The system SHALL show the user a list of saved conversations, most recent first. Each entry SHALL show when the conversation started and a short preview of its content.

#### Scenario: Conversations exist

- **WHEN** the user opens the conversation history and at least one conversation has been saved
- **THEN** the list shows every saved conversation, ordered by start time with the newest first

#### Scenario: Entry content

- **WHEN** a conversation appears in the list
- **THEN** its entry shows the start date and time and the beginning of its first message

#### Scenario: Conversation still in progress

- **WHEN** a saved conversation has no end time yet
- **THEN** it appears in the list and is marked as in progress

### Requirement: View a conversation transcript

The system SHALL let the user open a saved conversation and read all of its messages in the order they occurred, distinguishing messages from the user and messages from the agent.

#### Scenario: Open a conversation

- **WHEN** the user selects a conversation from the list
- **THEN** the system shows every message of that conversation in chronological order

#### Scenario: Speaker distinction

- **WHEN** the transcript is shown
- **THEN** each message is visibly attributed to either the user or the agent

#### Scenario: Message timestamps

- **WHEN** the transcript is shown
- **THEN** each message exposes the time it was recorded

#### Scenario: Unknown conversation

- **WHEN** the user requests a conversation that does not exist
- **THEN** the system tells the user the conversation was not found and offers a way back to the list

### Requirement: Empty and unavailable states

The system SHALL give the user a clear explanation when there is nothing to show, and SHALL distinguish "no conversations saved yet" from "history storage is unavailable".

#### Scenario: No conversations saved

- **WHEN** the history storage is reachable but contains no conversations
- **THEN** the list shows an empty state explaining that conversations will appear after a session

#### Scenario: Storage not configured

- **WHEN** no history storage location is configured
- **THEN** the system tells the user history is not set up and names the setting to provide

#### Scenario: Storage missing or unreadable

- **WHEN** a storage location is configured but cannot be read
- **THEN** the system tells the user history is unavailable instead of showing an empty list or crashing

### Requirement: Read-only access

The system SHALL NOT create, modify, or delete saved conversations. The history capability MUST work while the agent worker is writing new conversations to the same storage.

#### Scenario: No write operations

- **WHEN** any history request is made, whatever its method or parameters
- **THEN** the stored conversations are left unchanged

#### Scenario: Agent writing concurrently

- **WHEN** the agent worker is saving messages while the user browses history
- **THEN** the user can still list and open conversations without errors

### Requirement: Local development only

The system SHALL serve conversation history only in a local development environment, because it has no authentication and exposes private conversation content.

#### Scenario: Non-development environment

- **WHEN** a history request is made outside a development environment
- **THEN** the system refuses the request and returns no conversation content

### Requirement: Access from the welcome screen

The system SHALL let the user reach the conversation history from the welcome screen shown before a session starts.

#### Scenario: Entry point available

- **WHEN** the welcome screen is shown
- **THEN** it offers a way to open the conversation history

#### Scenario: Return to welcome

- **WHEN** the user is in the history views
- **THEN** they can return to the welcome screen

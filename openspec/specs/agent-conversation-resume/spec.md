# agent-conversation-resume Specification

## Purpose

Defines how the local agent worker acts on a request to resume or fork a saved conversation, so that the user can pick up an earlier conversation and the history file stays consistent.

## Requirements

### Requirement: Read the resume request

The system SHALL read, from the dispatch metadata of a session, a request naming a saved conversation and a mode of either continue or fork, and SHALL accept a persona id and a user id in the same metadata.

#### Scenario: Valid request

- **WHEN** a session starts with metadata naming an existing conversation and the mode continue or fork
- **THEN** the agent treats the session as a continued or forked conversation

#### Scenario: No metadata

- **WHEN** a session starts with no metadata
- **THEN** the agent runs an ordinary session recorded under the room name

#### Scenario: Persona beside a resume request

- **WHEN** the metadata holds both a resume request and a persona id
- **THEN** the resume request is read as usual and is not discarded because of the persona

#### Scenario: User id beside a resume request

- **WHEN** the metadata holds both a resume request and a user id
- **THEN** the resume request is read as usual and is not discarded because of the user id

### Requirement: Carry the earlier conversation into the session

The system SHALL give the model the earlier user and assistant messages of the named conversation, in their original order, so that it can continue the conversation.

#### Scenario: Earlier messages known to the model

- **WHEN** a conversation is continued or forked
- **THEN** the model answers the user's first turn knowing what was said earlier

#### Scenario: Long conversation

- **WHEN** the named conversation has more messages than the agent carries over
- **THEN** only the most recent ones are given to the model, in order

#### Scenario: Interrupted message

- **WHEN** an earlier agent message was interrupted
- **THEN** it is carried over as the text that was saved

### Requirement: Continue keeps the conversation

The system SHALL save the new messages of a continued conversation under its original id, leave its earlier messages unchanged, and mark it in progress until the session ends.

#### Scenario: Continued session runs

- **WHEN** a conversation is continued
- **THEN** its end time is cleared and new messages are saved under the original id

#### Scenario: Continued session ends

- **WHEN** a continued session closes
- **THEN** the conversation's end time is set again

#### Scenario: Earlier messages not duplicated

- **WHEN** a continued session closes
- **THEN** the earlier messages are not saved a second time

### Requirement: Fork creates a new conversation

The system SHALL save a forked session as a new conversation that records the conversation it was forked from, contains a copy of the carried-over messages, and leaves the source conversation unchanged.

#### Scenario: Fork starts

- **WHEN** a conversation is forked
- **THEN** a new conversation is saved with its own id, the source's id as its parent, and no end time

#### Scenario: Source left unchanged

- **WHEN** a forked session runs and ends
- **THEN** the source conversation's messages and times are unchanged

#### Scenario: Fork is a complete transcript

- **WHEN** a forked session has ended
- **THEN** its conversation contains the carried-over messages followed by the new ones

### Requirement: Greet on return

The system SHALL start a resumed or forked session with a short spoken greeting that acknowledges the earlier conversation, without waiting for the user to speak.

#### Scenario: Greeting on resume

- **WHEN** a conversation is continued or forked and the user joins
- **THEN** the agent speaks a brief greeting that refers to the earlier conversation

#### Scenario: Ordinary session

- **WHEN** a session has no resume request
- **THEN** the agent behaves as it did before this capability

### Requirement: Unusable requests never stop the session

The system SHALL run an ordinary session when the resume request cannot be used, and SHALL log the reason.

#### Scenario: Malformed metadata

- **WHEN** the metadata is not valid JSON or lacks a conversation id or a recognized mode
- **THEN** an ordinary session runs and a warning is logged

#### Scenario: Unknown conversation

- **WHEN** the named conversation does not exist in the history file
- **THEN** an ordinary session runs and a warning is logged

#### Scenario: History unavailable

- **WHEN** the history file is not configured or cannot be read
- **THEN** an ordinary session runs and a warning is logged

#### Scenario: Conversation with no messages

- **WHEN** the named conversation has no messages to carry over
- **THEN** an ordinary session runs and a warning is logged

### Requirement: Resumed session keeps the saved persona

The system SHALL run a continued or forked session with the persona saved with the original conversation, and SHALL ignore a persona id in the same metadata.

#### Scenario: Conversation with a saved persona

- **WHEN** a conversation saved with a persona is continued or forked
- **THEN** the session runs with that persona

#### Scenario: Conversation saved before personas existed

- **WHEN** a conversation with no saved persona is continued or forked
- **THEN** the session runs with the default persona

#### Scenario: Saved persona no longer exists

- **WHEN** the saved persona is not among the available personas
- **THEN** the default persona runs and a warning is logged

#### Scenario: Fork records the persona

- **WHEN** a conversation is forked
- **THEN** the new conversation is saved with the persona that ran it

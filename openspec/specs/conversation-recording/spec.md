# conversation-recording Specification

## Purpose

Defines how the local agent worker saves each live session to the shared history file, so that the history pages show real conversations and every agent records them the same way.

## Requirements

### Requirement: Record each session as a conversation

The system SHALL save every live session the agent worker takes part in as one conversation in the history file named by `CHAT_DB_PATH`, and SHALL create the file and its tables if they do not exist. A fresh session uses the room name as the conversation's identifier; a continued conversation keeps its original identifier, and a forked one records the conversation it came from.

#### Scenario: Session starts

- **WHEN** the agent worker begins a session in a room that is not resuming a saved conversation
- **THEN** a conversation is saved with the room name as its identifier, the start time, no end time, and the agent's dispatch name

#### Scenario: Session ends

- **WHEN** the session closes
- **THEN** the conversation's end time is set, and it no longer appears as in progress in the history pages

#### Scenario: History file does not exist yet

- **WHEN** a session starts and no history file exists at the configured path
- **THEN** the file and its tables are created and the session is recorded normally

#### Scenario: Concurrent reading

- **WHEN** the history pages read the file while a session is being recorded
- **THEN** the reader sees a consistent view and the recording is not blocked

#### Scenario: Continued session

- **WHEN** the agent worker begins a session that continues a saved conversation
- **THEN** the session is recorded under that conversation's original identifier, not the room name

#### Scenario: Forked session

- **WHEN** the agent worker begins a session that forks a saved conversation
- **THEN** a conversation is saved with the room name as its identifier and the source conversation's identifier as its parent

#### Scenario: History file created before forks existed

- **WHEN** a session starts and the history file's conversations have no parent reference yet
- **THEN** the reference is added without losing any saved conversation or message

### Requirement: Record the messages of a conversation

The system SHALL save each committed user and assistant message of a session under that session's conversation, once per message, in the order it occurred, and SHALL mark a message that was interrupted.

#### Scenario: Message committed

- **WHEN** the user or the agent finishes a message during a session
- **THEN** that message is saved with its role, its text and its time

#### Scenario: Message updated after first being saved

- **WHEN** a message that was already saved is committed again with changed content
- **THEN** the saved message is updated and no duplicate is created

#### Scenario: Interrupted message

- **WHEN** an agent message is cut off by the user
- **THEN** it is saved and marked as interrupted

#### Scenario: Other kinds of items

- **WHEN** a session produces items that are not user or assistant text, such as tool calls
- **THEN** they are not saved as messages

#### Scenario: Missed messages at the end

- **WHEN** the session closes and some committed messages were never saved
- **THEN** they are saved before the conversation is marked as ended

### Requirement: Recording never disrupts the session

The system SHALL keep the live session running when recording fails or is not configured.

#### Scenario: History location not configured

- **WHEN** `CHAT_DB_PATH` is not set
- **THEN** the session runs normally, nothing is recorded, and a warning is logged once

#### Scenario: Write failure

- **WHEN** saving a conversation or message fails during a session
- **THEN** the error is logged, the session continues, and later saves are still attempted

### Requirement: Recording is reusable by any agent

The system SHALL keep the recording behavior independent of what the agent says or does, so that any agent can record its sessions by attaching it, and SHALL store each agent's dispatch name with its conversations.

#### Scenario: Two agents record to the same file

- **WHEN** two different agents each run sessions against the same history file
- **THEN** each conversation is saved with the dispatch name of the agent that ran it

### Requirement: Local worker runs beside the app

The system SHALL let a developer run the agent worker locally under a dispatch name chosen by them, so that it receives sessions from the app without competing with a deployed agent of another name.

#### Scenario: Local worker named in the app configuration

- **WHEN** the app's `AGENT_NAME` equals the local worker's dispatch name and a call is started
- **THEN** the local worker joins the room and the session is recorded to the history file

#### Scenario: Recorded session is visible

- **WHEN** a recorded session has ended
- **THEN** it appears in the app's history list with its messages

### Requirement: Record the persona of a conversation

The system SHALL save, with each conversation, the id of the persona the agent ran it with, and SHALL add this to a history file created before personas existed without losing any saved conversation or message.

#### Scenario: Session with a persona

- **WHEN** a session runs with a persona
- **THEN** its conversation is saved with that persona's id

#### Scenario: History file created before personas existed

- **WHEN** a session starts and the history file's conversations have no persona yet
- **THEN** the persona field is added without losing any saved conversation or message

#### Scenario: Conversation saved before personas existed

- **WHEN** a conversation saved before personas existed is read
- **THEN** it has no persona and is treated as having run with the default persona

#### Scenario: Persona unusable

- **WHEN** the requested persona was unknown and the default ran
- **THEN** the conversation is saved with the default persona's id

### Requirement: Record the user of a conversation

The system SHALL save, with each conversation, the id of the user it was held with when the session was told one, and SHALL add this to a history file created before it existed without losing any saved conversation, message or persona.

#### Scenario: Session with a user id

- **WHEN** a session starts with a user id in its metadata
- **THEN** its conversation is saved with that id

#### Scenario: Session without a user id

- **WHEN** a session starts with no user id
- **THEN** its conversation is saved without one and the session runs as before

#### Scenario: Older history file

- **WHEN** the worker opens a history file saved before user ids existed
- **THEN** the file gains the new field and every earlier conversation and message is unchanged

#### Scenario: Continued conversation

- **WHEN** a conversation is continued
- **THEN** it keeps the user id it was first saved with

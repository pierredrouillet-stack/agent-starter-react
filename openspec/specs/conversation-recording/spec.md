# conversation-recording Specification

## Purpose

Defines how the local agent worker saves each live session to the shared history file, so that the history pages show real conversations and every agent records them the same way.

## Requirements

### Requirement: Record each session as a conversation

The system SHALL save every live session the agent worker takes part in as one conversation in the history file named by `CHAT_DB_PATH`, and SHALL create the file and its tables if they do not exist.

#### Scenario: Session starts

- **WHEN** the agent worker begins a session in a room
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

# Spec Delta

## MODIFIED Requirements

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

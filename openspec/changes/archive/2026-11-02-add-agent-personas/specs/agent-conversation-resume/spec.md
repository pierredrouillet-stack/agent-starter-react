# Spec Delta

## MODIFIED Requirements

### Requirement: Read the resume request

The system SHALL read, from the dispatch metadata of a session, a request naming a saved conversation and a mode of either continue or fork, and SHALL accept a persona id in the same metadata.

#### Scenario: Valid request

- **WHEN** a session starts with metadata naming an existing conversation and the mode continue or fork
- **THEN** the agent treats the session as a continued or forked conversation

#### Scenario: No metadata

- **WHEN** a session starts with no metadata
- **THEN** the agent runs an ordinary session recorded under the room name

#### Scenario: Persona beside a resume request

- **WHEN** the metadata holds both a resume request and a persona id
- **THEN** the resume request is read as usual and is not discarded because of the persona

## ADDED Requirements

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

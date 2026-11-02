# Spec Delta

## ADDED Requirements

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

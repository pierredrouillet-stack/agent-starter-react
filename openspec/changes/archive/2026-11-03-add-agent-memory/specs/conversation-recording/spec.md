# Spec Delta

## ADDED Requirements

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

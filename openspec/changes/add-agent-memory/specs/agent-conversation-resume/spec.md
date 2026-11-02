# Spec Delta

## MODIFIED Requirements

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

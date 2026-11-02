# Spec Delta

## Purpose

Defines how the agent worker holds several personas, each with its own goals and personality, and runs each session with the one requested.

## ADDED Requirements

### Requirement: Define personas

The system SHALL hold a fixed set of personas, each with an id, instructions that give it its personality and goal, and optionally its own voice and language model, and SHALL mark one as the default.

#### Scenario: Personas differ

- **WHEN** two sessions run with different personas
- **THEN** each agent follows its own persona's instructions

#### Scenario: Persona with its own voice

- **WHEN** a persona defines a voice
- **THEN** the agent speaks with that voice, and a persona without one uses the default voice

#### Scenario: Default persona unchanged

- **WHEN** a session runs with the default persona
- **THEN** the agent behaves as it did before personas existed

### Requirement: Run the requested persona

The system SHALL read a persona id from the dispatch metadata of a session and run the session with that persona.

#### Scenario: Known persona

- **WHEN** a session starts with metadata naming a persona that exists
- **THEN** the agent runs with that persona

#### Scenario: No persona requested

- **WHEN** a session starts with no metadata or no persona in it
- **THEN** the agent runs with the default persona

### Requirement: Unusable persona requests never stop the session

The system SHALL run the default persona when the requested persona cannot be used, and SHALL log the reason.

#### Scenario: Unknown persona id

- **WHEN** the metadata names a persona that does not exist
- **THEN** the default persona runs and a warning is logged

#### Scenario: Persona is not a string

- **WHEN** the persona in the metadata is not a non-empty string
- **THEN** the default persona runs and a warning is logged

### Requirement: Persona cannot change during a session

The system SHALL keep the persona chosen at the start of a session until the session ends.

#### Scenario: Session continues

- **WHEN** a session is running with a persona
- **THEN** no later input changes which persona is speaking

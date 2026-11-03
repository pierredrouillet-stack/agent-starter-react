# agent-personas Specification

## Purpose

Defines how the agent worker holds several personas, each with its own goals and personality, and runs each session with the one requested.

## Requirements

### Requirement: Define personas

The system SHALL hold a fixed set of personas, each with an id, instructions that give it its personality and goal, and optionally its own voice and language model, and SHALL mark one as the default.

#### Scenario: Personas differ

- **WHEN** two sessions run with different personas
- **THEN** each agent follows its own persona's instructions

#### Scenario: Persona with its own voice

- **WHEN** a persona defines a voice
- **THEN** the agent speaks with that voice, and a persona without one uses the default voice

#### Scenario: Default persona unchanged

- **WHEN** a session runs with the default persona and nothing is known about the user
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

### Requirement: Non-default personas are distinct characters

The system SHALL give each non-default persona a manner of its own, in how it words things, what it asks and how it reacts, beyond the task it performs, while keeping every reply suited to being spoken aloud.

#### Scenario: Same prompt, different persona

- **WHEN** the same user message is sent to two non-default personas
- **THEN** the replies differ in manner and not only in subject

#### Scenario: Character stays speakable

- **WHEN** a persona with a strong manner replies
- **THEN** the reply is still plain, brief spoken text under the rules shared by all personas

### Requirement: Personas may open the conversation

The system SHALL let a persona define an opener that the agent speaks when a fresh session starts, before the user says anything, and SHALL leave a persona without an opener silent until the user speaks.

#### Scenario: Persona with an opener

- **WHEN** a fresh session starts with a persona that defines an opener
- **THEN** the agent greets the user in that persona's manner without waiting

#### Scenario: Default persona

- **WHEN** a fresh session starts with the default persona
- **THEN** the agent waits for the user to speak, as before

#### Scenario: Resumed conversation

- **WHEN** a session resumes or forks a saved conversation
- **THEN** the agent welcomes the user back as it does today and the opener is not spoken

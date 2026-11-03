# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

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

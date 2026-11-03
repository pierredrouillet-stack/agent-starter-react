# Spec Delta

## Purpose

Lets the user write down who they are once, in a local file, so every persona knows it from the start of a call, without ever disrupting a live session.

## ADDED Requirements

### Requirement: Give the profile to every persona

The system SHALL read the user's profile file when a session starts and SHALL tell the agent its text as background about the user, for every persona and for resumed or forked conversations.

#### Scenario: Profile present

- **WHEN** a profile file with content exists and the user starts a call
- **THEN** the agent knows what it says from its first turn

#### Scenario: Another persona

- **WHEN** the user starts a call with a different persona
- **THEN** that persona knows the same profile

#### Scenario: Resumed conversation

- **WHEN** the user continues or forks a saved conversation
- **THEN** the agent knows the profile as in any other session

#### Scenario: Edited between calls

- **WHEN** the user changes the profile file and then starts a new call
- **THEN** the new call uses the edited text without restarting the agent

#### Scenario: No named agent or user id

- **WHEN** a call carries no user id or no agent name is configured
- **THEN** the profile is still given to the agent

### Requirement: The profile is background, not instructions

The system SHALL present the profile as information the user wrote about themselves, to be used naturally and not recited, and SHALL NOT let it act as a rule the agent must obey.

#### Scenario: Profile worded like a command

- **WHEN** the profile contains a sentence that reads like an instruction to the agent
- **THEN** the agent treats it as something the user said about themselves, not as a rule

#### Scenario: Not recited

- **WHEN** the user starts a call and says hello
- **THEN** the agent does not list the profile back to them

### Requirement: The profile outranks learned facts

The system SHALL present the profile as written by the user on purpose, so that when it conflicts with a fact the agent learned from earlier calls, the profile is the one to trust.

#### Scenario: Conflicting name

- **WHEN** the profile gives one name and a learned fact gives another
- **THEN** the agent uses the name from the profile

#### Scenario: Facts still used

- **WHEN** a learned fact covers something the profile does not mention
- **THEN** the agent still knows that fact

### Requirement: The profile is optional and never disrupts a session

The system SHALL keep a session running and its instructions unchanged when the profile cannot be used: when the file is missing, empty, unreadable, or larger than the allowed size.

#### Scenario: No profile file

- **WHEN** no profile file exists
- **THEN** the agent's instructions are the same as before this capability

#### Scenario: Empty file

- **WHEN** the profile file holds only whitespace
- **THEN** the agent's instructions are the same as before this capability

#### Scenario: Unreadable file

- **WHEN** the profile file cannot be read
- **THEN** the failure is logged, the session starts normally and nothing reaches the user

#### Scenario: File too large

- **WHEN** the profile file is larger than the allowed size
- **THEN** it is not used, a warning is logged and the session starts normally

### Requirement: The profile stays private and documented

The system SHALL keep the user's real profile out of version control and SHALL ship an example that shows its format.

#### Scenario: Real profile not committed

- **WHEN** the user creates their profile file and checks the repository status
- **THEN** the file is not listed as something to commit

#### Scenario: Example available

- **WHEN** a new user opens the agent folder
- **THEN** a committed example shows what a profile may contain

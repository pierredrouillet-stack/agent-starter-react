# agent-user-memory Specification

## Purpose

Lets the agent worker remember lasting facts about a user from earlier calls and use them in later ones, whichever persona is speaking, without ever disrupting a live session.

## Requirements

### Requirement: Extract lasting facts after a call

The system SHALL, once a session ends, read what the user said and save any lasting facts about them, such as their name, work, preferences and ongoing goals, under the user's id.

#### Scenario: User shares something lasting

- **WHEN** the user said during a call that they are a nurse who prefers short answers
- **THEN** facts recording the job and the preference are saved for that user

#### Scenario: Nothing lasting said

- **WHEN** the user only asked a one-off question and shared nothing about themselves
- **THEN** no fact is added

#### Scenario: Only the user's own words count

- **WHEN** the agent said something about the user that the user did not say or confirm
- **THEN** no fact is saved from it

### Requirement: Keep facts accurate and bounded

The system SHALL update a saved fact when the user says it has changed, SHALL remove a fact the user takes back, SHALL NOT keep duplicates, and SHALL keep each fact with the date it was learned and the conversation it came from. The number of facts kept for one user SHALL be limited.

#### Scenario: Fact changes

- **WHEN** the user says they have moved to a new job
- **THEN** the earlier job fact is replaced by the new one

#### Scenario: Fact taken back

- **WHEN** the user says to forget something they told the agent before
- **THEN** that fact is no longer saved

#### Scenario: Same fact twice

- **WHEN** a later call repeats a fact already saved
- **THEN** it is not saved a second time

#### Scenario: Too many facts

- **WHEN** a user has reached the limit and a new fact is learned
- **THEN** the oldest fact is dropped to make room

### Requirement: Give the facts to later sessions

The system SHALL tell the agent at the start of a session the facts saved for the user, as background about them and never as instructions, and SHALL do so for every persona and for resumed or forked conversations.

#### Scenario: Returning user

- **WHEN** a user with saved facts starts a call
- **THEN** the agent knows those facts from its first turn

#### Scenario: Another persona

- **WHEN** the user starts a call with a different persona than before
- **THEN** that persona knows the same facts

#### Scenario: Fact worded like an instruction

- **WHEN** a saved fact reads like a command to the agent
- **THEN** the agent treats it as something the user said, not as a rule it must obey

#### Scenario: New user

- **WHEN** a user with no saved facts starts a call
- **THEN** the agent behaves as it did before this capability

### Requirement: Memory is optional and never disrupts a session

The system SHALL keep a live session running and unchanged when memory cannot be used: when no user id is sent, no history file is configured, saved facts cannot be read, or extraction fails or is slow.

#### Scenario: No user id

- **WHEN** a session starts with no user id in its metadata
- **THEN** no facts are read or saved and the session runs as before

#### Scenario: No history file

- **WHEN** the history file is not configured
- **THEN** no facts are read or saved and the session runs as before

#### Scenario: Extraction fails

- **WHEN** reading the finished conversation or saving facts fails
- **THEN** the failure is logged, the facts already saved are unchanged, and nothing reaches the user

### Requirement: Facts stay inspectable and removable

The system SHALL keep facts in the shared history file in a documented, plain table, so that the user can see and delete what the agent believes about them.

#### Scenario: Reviewing facts

- **WHEN** the user opens the history file and lists the facts for their id
- **THEN** each fact is readable text with the date it was learned and the conversation it came from

#### Scenario: Deleting facts

- **WHEN** the user deletes a user's facts from the file
- **THEN** later sessions for that id start with no facts

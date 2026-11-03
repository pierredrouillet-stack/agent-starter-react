# user-identity Specification

## Purpose

Gives each browser a stable anonymous identity and tells a named agent about it, so the agent can recognise the same person across separate calls.

## Requirements

### Requirement: Keep a stable anonymous user id

The system SHALL give the browser a user id that is created once, is not derived from any personal information, and stays the same across page loads and calls until the browser's site data is cleared.

#### Scenario: First visit

- **WHEN** the app loads in a browser that has no user id
- **THEN** a new id is created and kept

#### Scenario: Later visit

- **WHEN** the app loads in a browser that already has a user id
- **THEN** the same id is used

#### Scenario: Browser storage unavailable

- **WHEN** the browser refuses to keep the id
- **THEN** the app still works and starts calls without an id, or with one that lasts only until the page closes

### Requirement: Tell the agent who is calling

The system SHALL send the user id to the agent with the dispatch metadata when a call starts, alongside any persona choice or resume request.

#### Scenario: Ordinary call

- **WHEN** the user starts a call with a persona selected
- **THEN** the agent is told the persona and the user id

#### Scenario: Call that resumes a conversation

- **WHEN** the user starts a call that resumes or forks a saved conversation
- **THEN** the agent is told the resume request and the user id

#### Scenario: Call started right after the page loads

- **WHEN** the user starts a call as soon as the page has loaded
- **THEN** the id the browser holds is sent, not a placeholder

### Requirement: Identity requires a named agent

The system SHALL send the user id only when the app dispatches a named agent, because an unnamed agent cannot receive metadata.

#### Scenario: No agent name configured

- **WHEN** no agent name is configured
- **THEN** no user id is sent and the call starts as it did before this capability

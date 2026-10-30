# Spec Delta

## Purpose

Lets the user return to a saved conversation and talk to the agent again, either by continuing the same conversation or by branching a new one from it, instead of only reading the log.

## ADDED Requirements

### Requirement: Offer resume and fork on a saved conversation

The system SHALL offer two actions on an opened saved conversation: Resume, which continues that conversation, and Fork, which starts a new conversation based on it.

#### Scenario: Actions shown for a finished conversation

- **WHEN** the user opens a saved conversation that has ended
- **THEN** the page offers both a Resume and a Fork action

#### Scenario: Conversation still in progress

- **WHEN** the user opens a saved conversation that is still in progress
- **THEN** neither action can be used and the page says why

#### Scenario: No messages to carry over

- **WHEN** the user opens a conversation that has no messages
- **THEN** neither action can be used

### Requirement: Start a live session from a saved conversation

The system SHALL start a live session with the agent when the user chooses Resume or Fork, and SHALL tell the agent which saved conversation to load and whether to continue it or fork it.

#### Scenario: Resume chosen

- **WHEN** the user chooses Resume on a saved conversation
- **THEN** a new live session starts and the agent is told to continue that conversation

#### Scenario: Fork chosen

- **WHEN** the user chooses Fork on a saved conversation
- **THEN** a new live session starts and the agent is told to start a new conversation based on that one

#### Scenario: Original left unchanged by a fork

- **WHEN** a forked session runs
- **THEN** the original conversation's messages are not changed by the frontend

### Requirement: Require a named agent

The system SHALL offer resume and fork only when the app is configured to dispatch a named agent, because an unnamed (automatically dispatched) agent cannot receive the conversation to load.

#### Scenario: No agent name configured

- **WHEN** the user opens a saved conversation and no agent name is configured
- **THEN** neither action can be used and the page says an agent name must be configured

#### Scenario: Agent name configured

- **WHEN** an agent name is configured and the conversation has ended
- **THEN** both actions are available

### Requirement: Show a pending resume before the call starts

The system SHALL show on the welcome screen which saved conversation will be resumed or forked, and SHALL let the user drop it and start an ordinary session instead.

#### Scenario: Pending resume shown

- **WHEN** the welcome screen is shown for a valid resume or fork request
- **THEN** it names the conversation and the chosen mode before the user starts the call

#### Scenario: Dropping the pending resume

- **WHEN** the user dismisses the pending resume
- **THEN** the next call starts as an ordinary session with no conversation to load

### Requirement: Validate the requested conversation

The system SHALL start a resumed or forked session only for a conversation that exists and has ended, and SHALL otherwise start no resumed session and tell the user why.

#### Scenario: Unknown conversation

- **WHEN** a resume or fork is requested for a conversation that does not exist
- **THEN** the system starts no session for it and tells the user the conversation was not found

#### Scenario: Conversation in progress

- **WHEN** a resume or fork is requested for a conversation that is still in progress
- **THEN** the system starts no session for it and tells the user it is still in progress

#### Scenario: Unrecognized mode

- **WHEN** a request names a mode other than resume or fork
- **THEN** the system treats it as an ordinary request with no resume

#### Scenario: History unavailable

- **WHEN** a resume or fork is requested while the history storage is not configured or cannot be read
- **THEN** the system starts no resumed session and tells the user history is unavailable

### Requirement: Resume and fork only in local development

The system SHALL honor resume and fork requests only in a local development environment, matching the history views.

#### Scenario: Non-development environment

- **WHEN** a resume or fork is requested outside a development environment
- **THEN** the system ignores the request and starts an ordinary session

### Requirement: Storage contract for resumed conversations

The system SHALL document, for the agent that writes conversations, how a resumed or forked conversation is identified, so both sides agree without sharing code.

#### Scenario: Continued conversation identity

- **WHEN** the agent is told to continue a saved conversation
- **THEN** the contract says new messages are saved under that conversation's original id and its end time is cleared while the session runs

#### Scenario: Forked conversation identity

- **WHEN** the agent is told to fork a saved conversation
- **THEN** the contract says a new conversation is saved with its own id and a reference to the conversation it was forked from

#### Scenario: Frontend stays read-only

- **WHEN** a session is resumed or forked
- **THEN** the frontend still does not create, modify, or delete any saved conversation

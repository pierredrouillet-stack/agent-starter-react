# Spec Delta

## Purpose

Lets the user choose which of several agent personas to talk to before starting a call, and tells the agent that choice.

## ADDED Requirements

### Requirement: Offer a choice of personas

The system SHALL show the available personas on the welcome screen, each with a name and a short description, and SHALL preselect the default persona.

#### Scenario: Welcome screen shown

- **WHEN** the welcome screen is shown with an agent name configured
- **THEN** every available persona is listed with its name and description, and the default one is selected

#### Scenario: Choosing another persona

- **WHEN** the user selects a different persona
- **THEN** that persona is marked as selected and the start button stays the single way to begin the call

### Requirement: Tell the agent the chosen persona

The system SHALL send the chosen persona's id to the agent with the dispatch metadata when the call starts, alongside any resume request.

#### Scenario: Persona chosen

- **WHEN** the user starts a call with a persona selected
- **THEN** the agent is told that persona's id

#### Scenario: Persona with a pending resume

- **WHEN** the call starts while a resume or fork is pending
- **THEN** the agent is told the resume request and no persona choice from the picker

### Requirement: Personas require a named agent

The system SHALL offer the persona choice only when the app dispatches a named agent, because an unnamed agent cannot receive the choice.

#### Scenario: No agent name configured

- **WHEN** the welcome screen is shown and no agent name is configured
- **THEN** no persona picker is shown and the call starts as it did before this capability

### Requirement: Hide the picker while a resume is pending

The system SHALL NOT show the persona picker while a resume or fork is pending, because the saved conversation already has a persona.

#### Scenario: Pending resume

- **WHEN** the welcome screen is shown for a valid resume or fork request
- **THEN** the persona picker is hidden

#### Scenario: Pending resume dropped

- **WHEN** the user drops the pending resume to start an ordinary session
- **THEN** the persona picker is shown with the default persona selected

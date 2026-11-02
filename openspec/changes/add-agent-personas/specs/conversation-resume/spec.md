# Spec Delta

## ADDED Requirements

### Requirement: Resume does not ask for a persona

The system SHALL start a resumed or forked session without a persona choice from the frontend, because the agent restores the persona of the saved conversation.

#### Scenario: Resume chosen

- **WHEN** the user chooses Resume or Fork on a saved conversation
- **THEN** the session starts without the user selecting a persona and the frontend sends none

#### Scenario: Storage contract documents the persona

- **WHEN** the contract for the agent that writes conversations is read
- **THEN** it describes the persona field of a conversation and the persona key of the dispatch metadata

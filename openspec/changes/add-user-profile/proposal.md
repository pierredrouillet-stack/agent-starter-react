# Proposal

## Why

Personas only know what `agent-user-memory` has learned from past calls, so on a fresh install, or after the facts are cleared, the agent does not even know the user's name. Since this is a single-user local app, the user can simply write down who they are once and have every persona know it from the first word.

## What Changes

- The agent reads a user-written profile file, `agent/profile.md`, when a session starts and gives its text to every persona as background about the user.
- The profile is placed before the learned facts in the prompt and is framed as written by the user, so it outranks a fact the agent picked up in passing. It is still data, never instructions.
- The profile is optional. With no file, an empty file, an unreadable file or an oversized file, the session runs exactly as it does today and any problem is logged.
- The real profile is gitignored; a committed `agent/profile.example.md` shows the format.
- The profile applies to every persona, including resumed and forked conversations, and needs no metadata, so it works with or without a named agent.

## Capabilities

### New Capabilities

- `user-profile`: the agent worker reads a user-written profile from a local file and gives it to every persona as background about the user, without ever disrupting a session.

### Modified Capabilities

None. `agent-user-memory` keeps its behavior; the profile is a separate source beside the learned facts.

## Impact

- `agent/src/personas.py` (prompt assembly), `agent/src/agent.py` (load the profile at session start), a small profile loader, and tests under `agent/tests/`.
- `agent/.gitignore`, a new `agent/profile.example.md`, and a short note in `agent/README.md`.
- No change to the React app, the token route, the dispatch metadata or the history file. The profile is personal data, kept in a local file and sent to the configured LLM provider with every prompt.

## Out of Scope

- A UI to view or edit the profile; it is edited as a plain file.
- Per-persona profiles, several users, or choosing a profile per call.
- Storing the profile in LiveKit Cloud (secrets or deployment settings).
- Changing how learned facts are extracted, stored or capped.
- Letting the agent edit the profile.

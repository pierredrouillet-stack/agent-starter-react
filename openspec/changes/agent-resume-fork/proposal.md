# Proposal

## Why

The change `resume-or-fork-conversation` makes the frontend send the agent a request to resume or fork a saved conversation, but the local agent worker ignores it, so both actions start an ordinary session. The agent has to read the request, give the model the earlier messages, and record the session under the right conversation.

## What Changes

- The agent worker reads the dispatch metadata `{"resume":{"conversation_id","mode":"continue"|"fork"}}` when a job starts.
- The earlier user and assistant messages of that conversation are loaded from the history file and given to the model as context, so the user can carry on where they stopped.
- **Continue**: new messages are saved under the original conversation id, and its end time is cleared while the session runs.
- **Fork**: a new conversation is saved under the room name, with `parent_id` pointing to the source. The source's messages are copied into it under new message ids, so the fork reads as a complete transcript and the original is never changed.
- The agent greets the user briefly on return, so the user knows the earlier conversation was loaded.
- The `conversations` table gains a nullable `parent_id` column, added to existing history files on first use.
- Missing, malformed or unusable metadata (bad JSON, unknown mode, unknown conversation, unreadable history) never stops the session: it runs as an ordinary one and the reason is logged.

## Capabilities

### New Capabilities

- `agent-conversation-resume`: how the agent worker acts on a request to resume or fork a saved conversation, including what it loads, how it greets, and what it does with an invalid request.

### Modified Capabilities

- `conversation-recording`: a session's conversation is no longer always identified by the room name (a continued conversation keeps its original id), and a forked conversation records the conversation it came from.

## Impact

- Code: `agent/src/recorder.py` (schema migration, `parent_id`, fork copy, loading messages), `agent/src/agent.py` (read metadata, seed context, greet), new tests in `agent/tests/`.
- Docs: `agent/README.md`, short note on running a resume locally.
- Dependencies: none new.
- Cross-change: relies on the metadata and storage contract written by `resume-or-fork-conversation` (task 1.1 in `docs/conversation-storage.md`). This change does not edit that document; if the contract moves, both changes follow it.

## Out of Scope

- Anything in the frontend: the actions, the validation, the banner, the metadata being sent.
- Showing the earlier messages in the live session view.
- Replaying tool calls or handoffs; only user and assistant text is carried over.
- Summarizing long conversations; only a fixed number of the latest messages is given to the model.
- Resume or fork for agents other than this local worker, and any authentication.

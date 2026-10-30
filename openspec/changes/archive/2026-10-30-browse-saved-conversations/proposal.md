# Proposal

## Why

Conversations with the LiveKit agent vanish when the session ends: the transcript lives only in React state (`useSessionMessages` in `agent-session-block.tsx`), and the app has no persistence. The user wants to re-read past conversations. The agent worker, which the user controls and runs locally with `dev`, sees every committed turn and is the right place to record them. This frontend needs a way to read and browse what the agent has saved.

## What Changes

- Add a read-only conversation history to the frontend: a list of saved conversations and a transcript view for one conversation.
- Read conversations on the server from a local SQLite file shared with the agent worker. The frontend never writes to it.
- Add an entry point to the history from the welcome view.
- Add a `CHAT_DB_PATH` environment variable (documented in `.env.example`) pointing at the SQLite file.
- Document the storage contract the agent worker must fulfil (file path, tables, columns, WAL mode). The agent-side writer is a dependency tracked in the agent repository, not a task here.
- Out of scope: writing conversations from the browser, long-term memory or fact extraction (Mem0 or similar), search, delete/edit, authentication, and a deployed (non-local) database.

## Capabilities

### New Capabilities

- `conversation-history`: Browsing previously saved agent conversations. Covers listing conversations, viewing one conversation's messages in order, behaviour when no database or no conversations exist, and the read-only guarantee.

### Modified Capabilities

<!-- None. openspec/specs/ is empty; no existing requirements change. -->

## Impact

- **New code**: history pages under `app/history/`, a small server-side data-access module, and a transcript view for stored messages.
- **Existing code touched**: `components/app/welcome-view.tsx` (entry link), `.env.example` (new variable). `components/agents-ui/agent-chat-transcript.tsx` is not edited; it takes live LiveKit `ReceivedMessage` objects, so the stored-message view is a separate component in `components/app/`.
- **Dependencies**: none added. Node 24 (the project's engine) includes `node:sqlite`; it requires the Node runtime, not Edge.
- **External dependency**: the agent worker must write to the shared SQLite file. Until it does, the history shows its empty state.
- **Security**: the history pages are local-only. They follow the token route's precedent of refusing to run outside development, since there is no authentication.

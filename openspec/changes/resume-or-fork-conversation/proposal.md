# Proposal

## Why

The history pages let the user re-read a saved conversation but not go back to it. Selecting a past conversation should let the user pick it up with the agent again, either by carrying on the same thread or by branching a new one from it, instead of only showing the log.

## What Changes

- The conversation transcript page offers two actions: **Resume** (continue the same conversation) and **Fork** (start a new conversation that begins from this one's context). Both are unavailable while the conversation is in progress.
- Choosing either action starts a new live session with the agent. The frontend tells the agent which conversation to load and in which mode, through the agent dispatch metadata sent when the session token is requested (the SDK's `agentMetadata` session option).
- The frontend validates the requested conversation against the saved history before using it, and ignores resume requests outside local development.
- The storage contract (`docs/conversation-storage.md`) gains an optional `conversations.parent_id` column for forks, a rule that `conversations.id` equals the room name only for fresh starts, and the dispatch-metadata shape the agent must read.
- A resumed conversation is written by the agent under its original id, and a fork under a new id with `parent_id` set. The frontend still never writes conversations.

## Capabilities

### New Capabilities

- `conversation-resume`: starting a live session from a saved conversation, either continuing it or forking it, including when the actions are offered, how the request reaches the agent, and what happens when the request is invalid.

### Modified Capabilities

<!-- None. The conversation-history requirements (read-only, dev-only, listing, transcript) are unchanged; the new actions are owned by conversation-resume. -->

## Impact

- Code: `app/history/[id]/page.tsx` (actions), `app/page.tsx` (read and validate the resume request), `components/app/app.tsx` (pass agent metadata to the session), `lib/conversations.ts` (check that a conversation exists and is not in progress).
- Docs: `docs/conversation-storage.md`.
- Dependencies: none new.
- Cross-repo: the agent worker must read the dispatch metadata, load the prior messages into its context, and write to the right conversation. Without that, the actions start an ordinary session. The agent repository is outside this change.

## Out of Scope

- Agent-side implementation (reading the metadata, seeding context, writing rows, greeting).
- Showing the earlier messages in the live session view; the live view starts empty.
- Replaying tool calls or handoffs; only user and assistant text is carried over.
- Truncating or summarizing very long conversations.
- Marking forks in the conversation list.
- Resume or fork outside local development, and any authentication.

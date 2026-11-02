# Design

## Context

The worker (`agent/src/agent.py`) builds an `AgentSession`, calls `recorder.attach(session, ctx, AGENT_NAME)`, then starts `Assistant()`. `attach` creates a `Recorder` keyed by `ctx.room.name`, saves committed user and assistant items as they arrive, and on close reconciles anything missed from `session.history` before setting `ended_at`. `start_conversation` already upserts and clears `ended_at` on conflict. The schema is created with `CREATE TABLE IF NOT EXISTS`, which does not add columns to an existing file. See proposal.md - Why.

Findings that shape the approach:

- The job metadata is available as `ctx.job.metadata` (a string). The frontend sends `{"resume":{"conversation_id","mode"}}` there (see `resume-or-fork-conversation`, design Decision 3).
- `Agent(chat_ctx=...)` seeds the model context without emitting `conversation_item_added`, so seeded messages are not re-recorded by the live handler. The close-time reconcile does walk `session.history`, so it must be told which ids are already saved.
- `messages.id` is the primary key, so a fork cannot reuse the source's message ids for its copy.
- LiveKit has no model hook for "the user has just arrived", so the greeting is an explicit `session.generate_reply`.

## Goals / Non-Goals

**Goals:**

- Resume logic isolated in `recorder.py` (storage) and one small block in `agent.py`, so other agents can adopt it by calling the same helpers.
- A resume request that cannot be honoured degrades to an ordinary session.

**Non-Goals:**

- Anything in the frontend, tool-call replay, or summarization (see proposal Out of Scope).

## Decisions

### 1. Parse and load before building the session

A pure `parse_resume(metadata: str) -> ResumeRequest | None` accepts only the documented shape and the two modes. `load_resume(conn, request)` returns the source conversation's carried messages or raises a typed failure (unknown conversation, no messages, history unavailable). `agent.py` calls both in `my_agent`, before `attach`, logs a warning on any failure and continues with `resume = None`. The pure parser and the loader are separate so each is testable without a session.

_Alternative:_ doing it inside `attach`. Rejected: `attach` runs before the agent exists, and the agent needs the loaded messages for its constructor.

### 2. Seed context through `Agent(chat_ctx=...)`

The most recent 100 saved user and assistant messages, oldest first, become a `ChatContext` passed to `Assistant(chat_ctx=...)`. The constant is a module-level default, not configuration. Interrupted messages are carried as their saved text.

_Alternative:_ `update_chat_ctx` after start. Rejected: it races the greeting and the user's first turn.

### 3. Identity per mode

`attach` takes an optional resume request. For continue, the `Recorder` is keyed by the source id, so `start_conversation`'s existing upsert clears `ended_at` and `end_conversation` sets it again. For fork, the `Recorder` is keyed by the room name and `start_conversation` writes `parent_id`. A fresh start is unchanged, which keeps the fresh-start rule "id equals room name" intact.

The room name is a fine id for a fork because every session gets a unique room, so no extra id generator is needed. Forking the same source twice therefore yields two sibling conversations.

### 4. Fork copies the carried messages

At fork start the carried messages are inserted into the new conversation with new ids (`<new id>:<n>`, keeping their original `created_at`, role, content and `interrupted`), then the new messages follow. This makes the fork a complete transcript in the existing history views, which read only by `conversation_id`. Copy and `start_conversation` run in one transaction. Only the carried window is copied, matching what the model saw.

_Alternative:_ reading parent messages through `parent_id` at display time. Rejected: it needs frontend changes this change must not make, and the shipped reader selects by `conversation_id`.

### 5. Do not re-record seeded items

`attach` pre-fills its `saved` set with the ids of the seeded items, so the close-time reconcile does not save them again. For continue this avoids rewriting rows; for fork the copy in Decision 4 already holds them under different ids and re-saving the originals would be a primary-key no-op at best.

### 6. Schema migration

`open_db` runs `PRAGMA table_info(conversations)` and issues `ALTER TABLE conversations ADD COLUMN parent_id TEXT` when the column is absent, after the `CREATE TABLE IF NOT EXISTS` script. New files get the column in `SCHEMA`. The reader selects explicit columns so no frontend change is needed, and the storage doc is updated by `resume-or-fork-conversation` task 1.1.

_Alternative:_ asking the developer to delete the file. Rejected: it loses saved conversations.

### 7. Greeting

After `session.start`, a resumed session calls `session.generate_reply(instructions=...)` asking for one short sentence welcoming the user back and naming the topic of the earlier conversation, without recapping it. Ordinary sessions do not greet, as today.

### 8. Reading and writing share one connection helper

The loader reads with the same `open_db` connection helper the writer uses. A read failure is caught in `agent.py` and downgraded to an ordinary session, consistent with the existing "recording never disrupts the session" rule.

## Risks / Trade-offs

- [The 100-message window drops the start of a very long conversation] → Acceptable for a local tool; the constant is one line to change, and a summary is out of scope.
- [A continued conversation is shown as in progress if the agent crashes] → Same as fresh sessions; unchanged.
- [Two sessions continue the same conversation at once] → Both write under one id and interleave. The frontend only offers Resume for an ended conversation, and concurrency across two tabs is not handled.
- [The seeded context makes the first turn slower or costlier] → Bounded by the 100-message window.
- [The contract drifts from the frontend's] → Both changes cite `docs/conversation-storage.md`; tasks verify the exact JSON shape against it.
- [Greeting wording is model-generated] → Instructions are constrained to one sentence; the wording itself is not specified.

## Migration Plan

1. Deploy by restarting the local worker; the first `open_db` call adds `parent_id` to an existing file. The change is additive, so the running frontend keeps working.
2. Rollback: revert the code. The extra nullable column is harmless to older code.

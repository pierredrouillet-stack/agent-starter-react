# Design

## Context

The app is a single page (`app/page.tsx`) whose client-side `ViewController` switches between `WelcomeView` and the live session view. There is no persistence and no database. The only server code is the token route handler, which refuses to run outside development because it has no authentication. See proposal.md - Why for motivation.

Constraints that shape the approach:

- The agent worker is a separate process, run locally with `dev`, and is the writer. It can read `conversation_item_added` events (user and agent turns, already committed) and `session.history` at close. The agent repo is out of scope here.
- The frontend and the agent share a disk, so a shared SQLite file is enough. A move to LiveKit Cloud later would break that; the design keeps all file access behind one module so that swap stays contained.
- `AgentChatTranscript` renders live LiveKit `ReceivedMessage` objects and decides alignment from `from?.isLocal` (a participant object), so it cannot render stored rows as they are.
- The project engine is Node 24.x, where `node:sqlite` is available without flags (verified with `DatabaseSync` on v24.15.0).

## Goals / Non-Goals

**Goals:**

- A read-only, server-side view of conversations the agent saved.
- A storage contract simple enough for the agent to implement without coordinating on code.
- Zero new runtime dependencies.

**Non-Goals:**

- Writing, editing or deleting conversations from the frontend.
- Search, pagination beyond a simple limit, export, or live-updating the list.
- Remote or deployed databases, authentication, multi-user separation.
- Tool calls, handoffs and latency metrics in the UI. The contract leaves room to add them later.

## Decisions

### 1. Shared SQLite file, agent owns the schema, frontend is read-only

The agent creates and migrates the database; this app opens it with `readOnly: true` and never issues DDL or writes. Two writers defining tables would drift.

_Alternatives:_ browser POST to a write endpoint (loses data when the tab closes, no tool calls); a small HTTP API on the agent (cleaner for a deployed agent, but another process to run, and unnecessary while both run locally); Postgres in Docker (heavier than a single-user local file).

### 2. Storage contract (the agent-side dependency)

The location comes from `CHAT_DB_PATH`, set in both repositories' env files. Journal mode is WAL so the agent can write while this app reads. Minimum tables and columns:

```
conversations
  id          TEXT PRIMARY KEY      -- stable; the room name is acceptable
  started_at  TEXT NOT NULL         -- ISO 8601 UTC
  ended_at    TEXT                  -- NULL while in progress
  agent_name  TEXT

messages
  id               TEXT PRIMARY KEY -- the LiveKit item id (upsert-friendly)
  conversation_id  TEXT NOT NULL REFERENCES conversations(id)
  role             TEXT NOT NULL    -- 'user' | 'assistant'
  content          TEXT NOT NULL
  created_at       TEXT NOT NULL    -- ISO 8601 UTC
  interrupted      INTEGER NOT NULL DEFAULT 0
```

The reader selects explicit columns, so the agent may add columns (latency, tool calls) without breaking it. Rows whose role is neither `user` nor `assistant` are ignored by the UI.

### 3. Server-rendered pages call a data module directly; no JSON route handlers

`app/history/page.tsx` (list) and `app/history/[id]/page.tsx` (transcript) are server components marked dynamic, so each request reads fresh data. They call one module, `lib/conversations.ts`, which owns opening the database, the queries, and mapping rows to plain objects. That module is the single boundary: replacing the file with an HTTP call to a remote agent later changes one file.

_Alternative:_ `/api/conversations` route handlers plus client fetching. Rejected for now: it adds an API surface, loading states and client state for a single-user local page. The earlier exploration assumed route handlers; this is the simpler way to meet the same spec.

### 4. Use `node:sqlite`, not a third-party driver

`DatabaseSync(path, { readOnly: true })` needs no install step. A native driver like `better-sqlite3` would add a build step under pnpm. The trade-off is that `node:sqlite` is still marked as an active-development API, accepted because the engine is pinned to Node 24.x and usage is two small queries. The pages must run on the Node runtime.

### 5. Open per request, fail soft

The module opens a read-only connection per call and closes it afterwards. Three outcomes map to the spec's states: `CHAT_DB_PATH` unset → "not configured"; path set but open or query fails (missing file, unreadable, missing tables) → "unavailable"; query succeeds with zero rows → "empty". Errors are logged on the server and never include file contents in the page.

### 6. Dev-only guard, like the token route

History pages check `NODE_ENV === 'development'` and otherwise return a not-found response without touching the database. Unlike the token route, they don't throw, because a thrown error would render an error page that hints at the route's existence.

### 7. A separate transcript component for stored messages

A new `StoredTranscript` in `components/app/` renders stored messages using the existing `ui/` primitives (`Message`, `Bubble`, `Streamdown`) so it looks like the live transcript. It takes `{ role, content, createdAt }[]`.

_Alternatives:_ build fake `ReceivedMessage` objects with a `from.isLocal` flag (couples storage to LiveKit client types and breaks on SDK changes); edit `AgentChatTranscript` (the file is installed from the shadcn registry and can be overwritten by `pnpm shadcn:install`).

### 8. Entry point

`WelcomeView` gains a "History" link to `/history`. The history pages carry a "Back" link to `/`. Navigation uses `next/link`, so no change to `ViewController` is needed.

## Risks / Trade-offs

- [Read-only connection on a WAL database needs the `-wal`/`-shm` files to be accessible] → The agent and app run as the same user on the same disk, so this holds locally. If it fails, the module reports "unavailable"; opening without `readOnly` while never writing is the fallback if needed.
- [`node:sqlite` API may change in a future Node release] → Engine is pinned to 24.x and the surface used is minimal; the data module is the only file to touch.
- [Agent and frontend disagree on the schema] → The contract in Decision 2 is the single source; the reader treats a missing table as "unavailable" rather than crashing.
- [Private conversation content is readable by anything that can reach the dev server] → Dev-only guard now. Publishing it beyond localhost requires an authentication layer first, noted as a non-goal.
- [Agent-side writer does not exist yet] → The history shows its empty state until it does. Verification during implementation can use a hand-made fixture database.

## Open Questions

- Should the agent record the conversation `title` or a summary later, to replace the "first message" preview? Deferrable; the UI can add it without changing the contract's required columns.

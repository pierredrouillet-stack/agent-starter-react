# Conversation storage contract

The `/history` pages of this app read conversations from a local SQLite file written by the agent
worker. This app is **read-only**: it never creates tables, migrates, or writes rows. The agent
creates and owns the schema.

## Location

Set `CHAT_DB_PATH` to the same absolute path in both this app's `.env.local` and the agent's
environment. If it is unset, `/history` shows a "not configured" message.

The history pages only run when `NODE_ENV=development` (they have no authentication).

## Journal mode

The agent MUST open the database in WAL mode so this app can read while the agent writes:

```sql
PRAGMA journal_mode = WAL;
```

Both processes need access to the `-wal` and `-shm` files next to the database, which holds when they
run as the same user on the same disk.

## Tables

```sql
CREATE TABLE IF NOT EXISTS conversations (
  id          TEXT PRIMARY KEY,   -- stable; the room name is acceptable
  started_at  TEXT NOT NULL,      -- ISO 8601 UTC
  ended_at    TEXT,               -- NULL while in progress
  agent_name  TEXT
);

CREATE TABLE IF NOT EXISTS messages (
  id               TEXT PRIMARY KEY,  -- the LiveKit item id (upsert-friendly)
  conversation_id  TEXT NOT NULL REFERENCES conversations(id),
  role             TEXT NOT NULL,     -- 'user' | 'assistant'
  content          TEXT NOT NULL,
  created_at       TEXT NOT NULL,     -- ISO 8601 UTC
  interrupted      INTEGER NOT NULL DEFAULT 0
);
```

The reader selects explicit columns, so extra columns (latency, tool calls, ...) can be added without
breaking it. Messages whose `role` is neither `user` nor `assistant` are ignored.

## What the agent should write

Use `AgentSession` events:

- **Session start**: insert a `conversations` row (`ended_at` NULL).
- **`conversation_item_added`**: upsert a `messages` row for each committed user or assistant item,
  keyed by the LiveKit item id. Set `interrupted = 1` when the item was interrupted.
- **Session close**: set `conversations.ended_at`. `session.history` can be used to reconcile any
  items missed.

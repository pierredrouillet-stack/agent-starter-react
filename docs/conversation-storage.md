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
  id          TEXT PRIMARY KEY,   -- stable; equals the room name only for fresh starts
  started_at  TEXT NOT NULL,      -- ISO 8601 UTC
  ended_at    TEXT,               -- NULL while in progress
  agent_name  TEXT,
  parent_id   TEXT REFERENCES conversations(id),  -- NULL unless forked from another conversation
  persona     TEXT,               -- id of the persona that ran it; NULL means the default persona
  user_id     TEXT                -- anonymous browser id the call was told about; NULL if none
);

CREATE TABLE IF NOT EXISTS messages (
  id               TEXT PRIMARY KEY,  -- the LiveKit item id (upsert-friendly)
  conversation_id  TEXT NOT NULL REFERENCES conversations(id),
  role             TEXT NOT NULL,     -- 'user' | 'assistant'
  content          TEXT NOT NULL,
  created_at       TEXT NOT NULL,     -- ISO 8601 UTC
  interrupted      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS user_facts (
  id                      INTEGER PRIMARY KEY,
  user_id                 TEXT NOT NULL,
  fact                    TEXT NOT NULL,      -- one short sentence the user said about themselves
  learned_at              TEXT NOT NULL,      -- ISO 8601 UTC
  source_conversation_id  TEXT                -- the conversation it was learned in
);

CREATE INDEX IF NOT EXISTS user_facts_user_id ON user_facts(user_id);
```

`persona` and `user_id` were added after the first version of this schema. The agent adds it to an older file with
`ALTER TABLE` when it opens it, so the app MUST NOT assume the columns exist. A conversation saved
before personas existed has `persona = NULL` and is treated as having run with the default persona.
`user_facts` is created when the agent opens the file, and the app never reads it.

The reader selects explicit columns, so extra columns (latency, tool calls, ...) can be added without
breaking it. Messages whose `role` is neither `user` nor `assistant` are ignored.

## What the agent should write

Use `AgentSession` events:

- **Session start**: insert a `conversations` row (`ended_at` NULL).
- **`conversation_item_added`**: upsert a `messages` row for each committed user or assistant item,
  keyed by the LiveKit item id. Set `interrupted = 1` when the item was interrupted.
- **Session close**: set `conversations.ended_at`. `session.history` can be used to reconcile any
  items missed.

## Resuming and forking

From a conversation's transcript page the user can **Resume** or **Fork** it. The app does not write
anything for this: it asks the agent to do so through the agent dispatch metadata, which LiveKit
delivers to the agent as `job.metadata`. Metadata is only delivered with explicit dispatch, so
`AGENT_NAME` MUST be set; with automatic dispatch the actions are disabled.

The metadata is a JSON string:

```json
{ "resume": { "conversation_id": "<conversations.id>", "mode": "continue" } }
```

`mode` is `continue` or `fork`. Without a `resume` key (or with empty metadata) the session is an
ordinary fresh start. Because the room name is generated per session, `conversations.id` only equals
the room name for fresh starts.

- **`continue`**: load the messages of `conversation_id` into the agent's context. Keep writing under
  that same `conversations.id` (the room name is different) and set `ended_at` back to NULL while the
  session runs, then set it again on close.
- **`fork`**: load the messages of `conversation_id` into the agent's context, then insert a new
  `conversations` row with its own id (the room name is fine) and `parent_id` set to
  `conversation_id`. Write new messages under the new id; the original conversation is left unchanged.

The app only offers these actions for conversations that have ended and have at least one message.

## Choosing a persona

The agent can run as one of several personas, each with its own instructions and optionally its own
voice. The welcome screen of this app lists them and sends the choice in the same dispatch metadata,
under a `persona` key next to `resume`. Both keys are optional:

```json
{ "persona": "tutor" }
```

```json
{
  "persona": "tutor",
  "resume": { "conversation_id": "<conversations.id>", "mode": "continue" }
}
```

- A missing, empty, non-string or unknown `persona` runs the agent's default persona, and the agent
  logs why. The call is never refused, and a valid `resume` is never dropped because of a bad persona.
- The agent writes the persona it actually ran to `conversations.persona`, so it holds the default
  persona's id when the requested one was unknown.
- On `continue` and `fork` the agent ignores the metadata's `persona` and runs the persona saved with
  `conversation_id` (the default when that is `NULL` or no longer exists). The app sends no persona
  with a resume. A fork stores the persona that ran it.

The ids live in two places that must be kept in step: `PERSONAS` in `agent/src/personas.py` (full
configuration) and `lib/personas.ts` (id, name and description for the picker). Like resume, this
needs explicit dispatch, so the picker is shown only when `AGENT_NAME` is set.

## Remembering the user

The browser keeps an anonymous id in `localStorage` and the app sends it as a `user` key in the same
dispatch metadata, next to `persona` and `resume`. All three keys are optional:

```json
{ "persona": "tutor", "user": "6f1c0d52-8a4e-4f0b-9d57-2f3f6c1d9a10" }
```

```json
{
  "user": "6f1c0d52-8a4e-4f0b-9d57-2f3f6c1d9a10",
  "resume": { "conversation_id": "<conversations.id>", "mode": "continue" }
}
```

- A missing, empty or non-string `user` means no memory: nothing is read or saved and the call runs as
  before. Like resume and personas, this needs explicit dispatch (`AGENT_NAME`), and the agent also
  needs `CHAT_DB_PATH`.
- The agent writes the id to `conversations.user_id`. A continued conversation keeps the id it was
  first saved with.
- After a call ends the agent makes one extra LLM call over what the user said, and adds, removes or
  replaces rows of `user_facts` for that id. It keeps at most 50 facts per user (the oldest are
  dropped) and cuts each at 200 characters. If that call fails or runs past 6 seconds, nothing is
  changed.
- At the start of every call, for any persona, the agent puts the user's facts in its instructions as
  background about the user, one line each with the date it was learned.

The id is not a secret and anyone with the file can read every fact, so treat it like the rest of this
local development file.

### Listing and deleting facts

The tables are plain SQLite. Find ids with `SELECT DISTINCT user_id FROM conversations;`, then, with
`<user id>` replaced by one of them:

```sql
SELECT id, fact, learned_at, source_conversation_id FROM user_facts WHERE user_id = '<user id>' ORDER BY learned_at, id;
```

```sql
DELETE FROM user_facts WHERE id = 3;
```

```sql
DELETE FROM user_facts WHERE user_id = '<user id>';
```

Calls that start after a delete see the change. The agent writes facts when a call ends, so delete
while no call for that user is ending.

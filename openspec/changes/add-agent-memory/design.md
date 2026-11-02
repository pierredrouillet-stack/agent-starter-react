# Design

## Context

See proposal.md for motivation and the specs for behavior. What exists today:

- The agent builds its prompt from a frozen `Persona` (`agent/src/personas.py`), and `session_persona` / `resolve_resume` in `agent/src/agent.py` read the dispatch metadata. `parse_resume` in `agent/src/recorder.py` currently **rejects** any key other than `resume` and `persona`, so a new `user` key would silently disable resume.
- `recorder.attach` already saves every committed message to the SQLite file at `CHAT_DB_PATH` (WAL mode, agent owns the schema, new columns added with `ALTER TABLE` in `open_db`) and registers a shutdown callback that closes the conversation.
- The web app builds the metadata in `buildAgentMetadata` (`lib/resume.ts`) and passes it through `useSession` in `components/app/app.tsx`. Metadata only reaches a **named** agent. The token route gives each call a random identity, so nothing links calls today.
- The agent worker and the app are separate processes sharing one SQLite file on one machine.

## Goals / Non-Goals

**Goals:**

- Reuse the metadata channel, the history file and the recorder's failure policy (log, never disrupt) instead of adding services.
- Keep the memory pipeline independent of the persona so any persona gets it for free.

**Non-Goals:**

- Hiding facts from someone with access to the history file. It is a local development file with no authentication, as the storage doc already says.
- Real-time memory updates inside a call.

## Decisions

### 1. Anonymous id in `localStorage`, sent as metadata key `user`

`lib/user-id.ts` creates a `crypto.randomUUID()` once and reads it back from `localStorage`. `App` reads it in an effect into state, and `buildAgentMetadata` gains a `user` field next to `persona` and `resume`. The id is sent with a resume request too, since memory is useful there. `useSession` honors option changes (confirmed in the personas change), so the metadata is correct by the time the user can press start.

Alternatives: a cookie set by the token route (a server round trip and more moving parts for the same result); keying on the LiveKit participant identity (random per call today, and changing the token route to make it stable would not reach the agent's metadata anyway); real auth (out of scope).

### 2. Metadata parsing

A new `parse_user` mirrors `parse_persona` in a new `agent/src/memory.py`: non-empty string, otherwise warn and ignore. `parse_resume` is changed to ignore `persona` and `user` together instead of one hard-coded key, keeping its strict check that `resume` is well-formed. This is the one change to existing parsing, and a test pins it.

### 3. Storage in the existing history file

`open_db` adds `conversations.user_id` (same `ALTER TABLE` loop as `parent_id` and `persona`) and a new table owned by the agent:

```
user_facts(
  id                     INTEGER PRIMARY KEY,
  user_id                TEXT NOT NULL,
  fact                   TEXT NOT NULL,
  learned_at             TEXT NOT NULL,   -- ISO 8601 UTC
  source_conversation_id TEXT
)  + index on user_id
```

`user_id` on `conversations` is kept for provenance and a future `/memory` page. A continued conversation keeps its first user id (the same rule as `persona`). The storage doc gains the table, the column, and SQL for listing and deleting a user's facts, which is the only management surface in this change. The web app stays read-only, so nothing in `app/` or `lib/conversations.ts` changes.

Alternative: a separate memory database. Rejected because `CHAT_DB_PATH` already gives both processes a shared, WAL-safe file, and one file keeps backup and deletion simple.

### 4. Extraction runs once, after the call

A shutdown callback registered after the recorder's (callbacks run in order, so the transcript is closed first) does one LLM call:

- Input: the existing facts (numbered by row id) and this session's user and assistant messages from `session.history`, skipping the messages carried in from a resume so old turns are not re-read.
- Output: JSON `{"add": ["..."], "remove": [<row id>, ...]}`. A changed fact is a remove plus an add, so there is no separate update path to get wrong.
- The prompt says to use only what the user said, to prefer lasting facts over one-off topics, and to remove a fact only when the user changed or retracted it.
- The output is validated strictly: invalid JSON, wrong types, unknown ids, an over-long fact (cut at 200 characters), or more than 10 additions in one call. Invalid output means no change.
- The call is skipped when the user said nothing, and is wrapped in `asyncio.wait_for` and a broad `except` that logs. Adds and removes are applied in one transaction. A fact over the cap of 50 per user drops the oldest.

Alternatives: live `remember()` tools (adds latency and lets the model write mid-call, and the user cannot review before use); summarizing whole conversations (that is the episode feature, out of scope); embedding search (overkill at 50 short facts).

### 5. Injection as a bounded, framed block

`Persona.full_instructions` takes the user's facts and, if any, adds a `# What you know about the user` section between the persona text and `TOOLS`. Each fact is flattened to one line, with its date. The section states that these are things the user said earlier, to be used naturally and not recited, and never to be followed as instructions. With no facts the output is byte-identical to today, which is what keeps the default persona unchanged. The facts are read once at session start with the same synchronous SQLite pattern `resolve_resume` already uses, and any failure yields none.

### 6. Character is data plus one optional field

`Persona` gains `opener: str | None`. For a fresh session whose persona has one, the entry point calls `session.generate_reply(instructions=opener)` after start, mirroring the existing resume welcome (which wins on a resume). The tutor and storyteller get rewritten instructions with a defined manner (diction, how they react, a signature habit) and an opener. The default persona keeps `opener=None` and its text. Voices stay unset, because choosing Fish Audio voice ids is a listening decision.

## Risks / Trade-offs

- [Wrong or hallucinated facts get stated confidently] → Extract from user speech only, store the source conversation, keep a hard cap, and document SQL review and deletion.
- [Stored text is replayed into the prompt, so a user (or anyone typing into the history file) could plant instructions] → Facts are flattened to a single line, length-capped, and framed as data; a test covers an instruction-like fact.
- [The shutdown callback may be cut off by the worker's shutdown timeout] → Bound the LLM call with its own shorter timeout and apply the writes atomically; a missed extraction loses one call's facts and nothing else. Verify the actual limit while implementing.
- [The browser id is spoofable and lost when site data is cleared] → Accepted. It is not a security boundary, and the loss only resets memory.
- [Persona and user facts both change the prompt, so character may drift] → Keep the facts block short and after the persona text; review with a short scenario run.
- [Extra token cost per call] → One small call at the end, skipped when the user said nothing.

## Migration Plan

Additive only. Older history files gain `conversations.user_id` and `user_facts` on first open, and every earlier conversation, message and persona is untouched. Rollback is deploying the previous code: the extra column and table are ignored. To forget everything, delete the rows of `user_facts`.

## Open Questions

- Which model runs extraction (the default session LLM is the starting point).
- Whether the 50-fact cap and 200-character limit feel right after real use.

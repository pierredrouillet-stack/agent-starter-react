# Proposal

## Why

The personas shipped in `add-agent-personas` are job descriptions rather than characters, and every call starts from zero: the agent gets a random browser identity and a random room, so it cannot know who is talking to it or what they said last week. Giving personas a real character and letting the agent remember facts about the user makes it feel like one continuing relationship instead of a stateless bot.

## What Changes

- Make the non-default personas distinct characters: richer instructions in their own manner, and an optional spoken opener so the character shows before the user speaks. The default persona is untouched.
- Give the browser a stable anonymous user id (generated once, kept in `localStorage`) and send it to the agent in the dispatch metadata, alongside any persona or resume request.
- Teach the agent to remember facts about the user. After each call it reads what the user said, merges any lasting facts (name, job, preferences, ongoing goals) into a facts table in the shared history file, and keeps them dated and sourced.
- At the start of a session, inject the user's saved facts into the agent's instructions as background data. Facts are shared by every persona.
- Record the user id with each conversation so facts and conversations can be tied together.
- The resume-request parser must stop rejecting the new `user` metadata key.

Memory works only when the app dispatches a named agent (metadata is not delivered otherwise) and `CHAT_DB_PATH` is set. In any other case the agent behaves as it does today.

## Capabilities

### New Capabilities

- `user-identity`: the web app keeps a stable anonymous user id in the browser and sends it to a named agent with the dispatch metadata.
- `agent-user-memory`: the agent worker extracts lasting facts about the user after a call, stores them, and gives them to later sessions of any persona; failures never disrupt a session.

### Modified Capabilities

- `agent-personas`: personas gain an optional opener, and the non-default personas are required to read as distinct characters; the default persona stays as it was.
- `agent-conversation-resume`: the metadata reader accepts a user id beside the resume request and persona.
- `conversation-recording`: each conversation is saved with the id of the user it belongs to, added to older history files without losing data.

## Impact

- `agent/src/personas.py`, `agent/src/agent.py`, `agent/src/recorder.py`, a new `agent/src/memory.py`, and tests under `agent/tests/`.
- `components/app/app.tsx`, `lib/resume.ts`, and a new `lib/user-id.ts`.
- `docs/conversation-storage.md`: the `user_id` column, the facts table, and how to inspect or delete facts with SQL.
- One extra LLM call per call, after it ends. Facts are personal data in a local, unauthenticated SQLite file.

## Out of Scope

- A `/memory` page to view or edit facts (a follow-up; until then facts are managed with SQL).
- Per-conversation episode summaries, goals and open loops, and per-persona memory.
- Real authentication or multiple users on one device; the browser id is spoofable and is not a security boundary.
- Live `remember()` tools called mid-conversation.
- Choosing new TTS voices for personas.

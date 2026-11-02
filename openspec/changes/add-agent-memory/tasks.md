# Tasks

## 1. Metadata and storage on the agent

- [x] 1.1 Create `agent/src/memory.py` with `parse_user` (non-empty string, otherwise warn and return None) and relax `parse_resume` to ignore `persona` and `user` together while keeping every check on the `resume` body; verify with tests that existing `parse_resume` rejection cases still reject, that `{"user": "u", "resume": {...}}` yields the resume request, and that a non-string or empty user id is ignored with a warning
- [x] 1.2 Add the nullable `user_id` column to the schema and to `open_db`'s in-place migration, and write it in `start_conversation` (kept on a continued conversation); verify with tests that an old file gains the column without losing conversations, messages or personas, and that a new conversation stores its user id
- [x] 1.3 Add the `user_facts` table and index to the schema, plus helpers to load a user's facts, apply adds and removes in one transaction, and drop the oldest beyond the cap of 50; verify with tests for add, remove, duplicate text, cap eviction and rollback on a failing write
- [x] 1.4 Pass the user id from `my_agent` through `attach`/`Recorder`; verify `uv run ruff check`, `uv run ruff format --check` and `uv run pytest` pass in `agent/`

## 2. Fact extraction after a call

- [x] 2.1 Look up the current LiveKit Agents API for a one-off LLM call outside a session (use the `reading-livekit-docs` skill), then write `extract_facts` that builds the prompt from the numbered existing facts and this session's messages (skipping messages carried in from a resume) and parses the reply; verify with tests that feed canned model replies for valid, invalid JSON, wrong types, unknown ids, over-long facts and more than 10 adds
- [x] 2.2 Register an extraction shutdown callback after the recorder's, skipped when the session has no user id, no `CHAT_DB_PATH` or no user message, bounded by a timeout and a broad logged `except`; verify with tests that a raising or timing-out model leaves facts unchanged and that the session close is not affected
- [x] 2.3 Document the `user` metadata key, the `user_id` column, the `user_facts` table, and the SQL to list and delete a user's facts in `docs/conversation-storage.md` and `agent/README.md`; verify the documented metadata example and SQL run against a seeded file in a test

## 3. Facts in the prompt

- [x] 3.1 Give `Persona.full_instructions` the user's facts and render the `# What you know about the user` section (one line per fact with its date, flattened and length-capped, framed as background); verify with tests that no facts yield output identical to today's prompt for every persona and that a multi-line, instruction-like fact stays on one framed line
- [ ] 3.2 Load the user's facts at session start (any failure yields none) and pass them into `Assistant`, including for resumed and forked sessions and for every persona; verify with tests that two personas receive the same facts and that a missing database yields the unchanged prompt
- [ ] 3.3 Run `uv run pytest` in `agent/` and confirm `test_agent.py` still passes with the default persona

## 4. Distinct characters

- [ ] 4.1 Add an optional `opener` to `Persona` and speak it with `session.generate_reply` after start for a fresh session only (the resume welcome wins on a resume); verify with tests for opener present, absent and resumed
- [ ] 4.2 Rewrite the tutor and storyteller instructions as characters (diction, reactions, a signature habit) that still obey the shared output rules, and give each an opener; keep the default persona and its text unchanged; verify the default-prompt test still passes and that each persona's text differs in more than the task description
- [ ] 4.3 Add a short simulation scenario per rewritten persona to `agent/scenarios.yaml` checking its manner and that replies stay plain spoken text; verify by running the scenarios per the `running-livekit-simulations` skill and noting the result

## 5. User id in the web app

- [ ] 5.1 Add `lib/user-id.ts` that creates and reads the id in `localStorage`, tolerating unavailable storage, and extend `buildAgentMetadata` in `lib/resume.ts` with a `user` field; verify with `pnpm lint`, `pnpm format:check`, `pnpm build` and by reading the produced JSON for persona-only, resume-only, both, and each with a user id
- [ ] 5.2 Read the id into state in `App` after mount and pass it in the session options only when `agentName` is set; verify in dev that the metadata reaching the token request holds the same id after a reload and none when `AGENT_NAME` is blank

## 6. End-to-end check

- [ ] 6.1 Run the worker and the app locally with `AGENT_NAME` and `CHAT_DB_PATH` set, tell the agent a name and a preference in one call, then start a second call with a different persona and confirm it knows both; verify in the SQLite file that `conversations.user_id` and `user_facts` rows exist with dates and sources, and note the runs
- [ ] 6.2 Confirm the failure paths by starting a call with `CHAT_DB_PATH` unset and with a cleared browser id; verify the call runs normally and no facts are read or written

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.

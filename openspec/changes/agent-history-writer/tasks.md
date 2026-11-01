# Tasks

## 1. Scaffold the worker

- [x] 1.1 Scaffold a Python agent into `agent/` with `lk agent init` (no `--deploy`), set up its environment with `uv`, and add `agent/` build artifacts (virtualenv, caches, `.env.local`) to `.gitignore`; verify `lk agent list` shows no new agent and `git status` shows only source files from the scaffold.
- [x] 1.2 Give the worker a local dispatch name read from `AGENT_NAME` in `agent/.env.local` (default `pierre-assistant-dev`), and document the variables in `agent/.env.example`; verify `uv run python src/agent.py dev` (or the scaffold's equivalent) starts and logs that it registered under that name.

## 2. Recorder module

- [x] 2.1 Add the recorder's storage part: open `CHAT_DB_PATH` in WAL mode with a busy timeout, create the two tables from `docs/conversation-storage.md` if missing, and expose functions to start a conversation, upsert a message and end a conversation; verify with a one-off script that a fresh path gets the tables and that `PRAGMA journal_mode` reads `wal`.
- [x] 2.2 Make every storage call log and swallow errors, and make an unset `CHAT_DB_PATH` log one warning and turn recording off; verify with a one-off run that an unwritable path and an unset variable both leave the calling code running.
- [ ] 2.3 Add the session wiring: one `attach` call that takes the session, job context and dispatch name, inserts the conversation on start, saves user and assistant text items on `conversation_item_added` (skipping other item types, setting `interrupted`), and on close saves any missed items from `session.history` then sets `ended_at` (also on job shutdown); verify event and field names against the installed `livekit-agents` docs and with a stub session that emits a message, an interrupted message, a tool item and a close.

## 3. Wire the agent

- [ ] 3.1 Call `attach` from the agent's entrypoint with the dispatch name; verify the diff to the entrypoint is only that call and its import.

## 4. Verify end to end

- [ ] 4.1 Point `CHAT_DB_PATH` (app and worker) at a fresh file, start the worker and `pnpm dev` with the app's `AGENT_NAME` set to the worker's name, hold a short call, and verify a row appears in `conversations` with the room name, the worker's dispatch name and a null `ended_at`, and that `/history` lists it as in progress.
- [ ] 4.2 End the call and verify `ended_at` is set, the messages from both sides are in `/history/<id>` in order, and an interrupted reply (talk over the agent) is saved with `interrupted = 1`.
- [ ] 4.3 Unset `CHAT_DB_PATH` for the worker and verify a call still works with one warning in the worker log and no new rows.

## 5. Docs

- [ ] 5.1 Update `README.md` with how to run the worker, which `AGENT_NAME` and `CHAT_DB_PATH` to set on each side, that the cloud agent must use a different name, and how to confirm a conversation was saved; add any clarification to `docs/conversation-storage.md` that implementation revealed; verify by following the README steps from a clean shell.
- [ ] 5.2 Run `pnpm lint`, `pnpm format:check` and `pnpm build`; verify all three pass and the app is unchanged.

## Workflow follow-up

- The multi-agent picker is a separate change (`multi-agent-picker`), planned after this one.
- Archive the change after review.

# Tasks

## 1. Schema

- [x] 1.1 Add the nullable `parent_id` column to `SCHEMA` in `agent/src/recorder.py` and add the `PRAGMA table_info` check with `ALTER TABLE ... ADD COLUMN` to `open_db`; add `agent/tests/test_recorder.py` cases for a new file and for a file created with the old schema holding a conversation and a message, and verify `uv run pytest agent/tests/test_recorder.py` passes and the old rows survive.

## 2. Request and loading

- [x] 2.1 Add `parse_resume(metadata)` to `agent/src/recorder.py`, accepting only `{"resume":{"conversation_id","mode":"continue"|"fork"}}`; add tests for valid continue and fork, empty string, invalid JSON, a missing id, an unknown mode and extra fields, and verify they all pass.
- [x] 2.2 Add `load_resume(conn, request)` returning the latest 100 user and assistant messages of the source oldest first, and raising a typed failure for an unknown conversation or no messages; add tests with a seeded database for order, the 100 cap, ignored non-chat roles, unknown id and empty conversation, and verify they pass.

## 3. Recording by mode

- [x] 3.1 Extend `start_conversation` and `Recorder` to key a continued session by the source id (clearing `ended_at`) and a forked session by the room name with `parent_id`; add tests that continue clears `ended_at` and keeps `started_at` and that fork writes `parent_id`, and verify they pass.
- [x] 3.2 Copy the carried messages into a fork with new ids `<new id>:<n>` in the same transaction as `start_conversation`; add tests that the fork holds the copied messages with original times and content, that the source rows are unchanged, and that a failure leaves no partial fork, and verify they pass.
- [ ] 3.3 Let `attach` accept the resume request and pre-fill its `saved` set with the seeded item ids so the close-time reconcile skips them; add a test with a fake session whose history holds seeded and new items, and verify the earlier messages are not saved again and the new ones are, under the right conversation id for both modes.

## 4. Agent wiring

- [ ] 4.1 In `agent/src/agent.py` read `ctx.job.metadata`, call `parse_resume` and `load_resume`, log a warning and continue as an ordinary session on any failure, build a `ChatContext` from the carried messages and pass it to `Assistant(chat_ctx=...)`; add a test with a stub context covering malformed metadata, an unknown conversation and a valid request, and verify the ordinary path is unchanged for all failures.
- [ ] 4.2 After `session.start`, call `session.generate_reply` with a one-sentence welcome-back instruction only for a resumed session; verify with the agent debugger (`lk agent debugger`) that a resumed session greets first and refers to the earlier topic, and that an ordinary session does not greet.

## 5. Integration

- [ ] 5.1 Document in `agent/README.md` how to resume locally (named agent, `CHAT_DB_PATH`, the metadata shape, the 100-message window), pointing at `docs/conversation-storage.md` for the contract; verify the commands run as written against a seeded database.
- [ ] 5.2 Run `uv run ruff check` and `uv run ruff format --check` in `agent/`, then `uv run pytest`; verify all pass.
- [ ] 5.3 With the frontend change in place, start one Resume and one Fork from `/history`, and verify in `/history` that the continued conversation gained messages under its original id, the fork is a new conversation holding the copy plus new messages, and the source is untouched; if the frontend is not ready, replay the documented JSON through the debugger instead and record which was used in the PR description.

## Workflow follow-up

- Archive this change together with, or after, `resume-or-fork-conversation`; the `conversation-recording` delta here must be synced to the main spec on archive.

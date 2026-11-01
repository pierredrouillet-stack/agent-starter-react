# Proposal

## Why

The `/history` pages read conversations from a local SQLite file, but nothing writes to it. The only rows in it are fixture data from `scripts/seed-chat-db.mjs`. The agent being used today, `pierre-assistant`, runs on LiveKit Cloud and cannot reach a file on the developer's machine. History therefore never shows a real conversation. This is also the first step toward choosing between several agents: every agent has to record its conversations the same way.

## What Changes

- Add a Python agent worker to this repository, scaffolded with `lk agent init`, that runs locally (`lk agent dev`) under its own dispatch name, separate from the deployed cloud agent.
- The worker records each session to the SQLite file named by `CHAT_DB_PATH`, following `docs/conversation-storage.md`: it creates the tables in WAL mode, inserts a conversation when the session starts, saves each user and assistant message as it is committed, and sets the end time when the session closes.
- The recording code is a single small module, separate from the agent's behavior, so a later agent can reuse it. Each row carries the agent's dispatch name in `conversations.agent_name`.
- Recording problems never interrupt the voice session. If `CHAT_DB_PATH` is not set, recording is switched off with a warning.
- Document in the README how to run the worker, which `AGENT_NAME` to set, and how to confirm a conversation was saved.

## Capabilities

### New Capabilities

- `conversation-recording`: how the agent worker saves each live session to the shared history file, so that the history pages can show real conversations.

### Modified Capabilities

<!-- None. The frontend's read-only history requirements are unchanged. -->

## Impact

- Code: new `agent/` directory (Python, managed with `uv`) containing the worker and the recording module.
- Docs: `docs/conversation-storage.md` (small clarifications only), `README.md` (how to run the worker).
- Config: `.env.local` needs `AGENT_NAME` set to the local worker's dispatch name and `CHAT_DB_PATH` set to the same absolute path used by the worker.
- Dependencies: Python tooling for the `agent/` directory only; none added to the Next.js app.
- Existing behavior: the frontend does not change.

## Out of Scope

- The multi-agent picker (a separate follow-up change).
- Resume and fork handling by the agent, which belongs to `resume-or-fork-conversation`.
- Writing history from the cloud-deployed agent, or any storage other than the local SQLite file.
- Changing, redeploying or deleting the existing cloud agents.
- Recording tool calls, handoffs, audio or video; only user and assistant text is saved.
- Authentication, retention or deletion of saved conversations.

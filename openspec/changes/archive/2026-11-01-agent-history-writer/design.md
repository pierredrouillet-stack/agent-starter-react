# Design

## Context

The history pages read `CHAT_DB_PATH` through `lib/conversations.ts` and expect the schema in `docs/conversation-storage.md`; nothing writes that file yet. The agent in use, `pierre-assistant`, is deployed to LiveKit Cloud, so it runs on LiveKit's machines and cannot write to the developer's disk. A worker that does write must run on the same machine and user as the app. See proposal.md - Why.

Findings that shape the approach:

- The app's `AGENT_NAME` selects the agent by dispatch name. Two workers registered under the same name would share sessions, so a local worker needs a different name from the cloud agent.
- `lk agent init` scaffolds a project from a template, and only deploys with the explicit `--deploy` flag.
- The schema is fixed by the contract; the frontend selects explicit columns, so extra columns are harmless.

## Goals / Non-Goals

**Goals:**

- A local worker whose sessions appear as real conversations in `/history`.
- Recording kept in one module with no knowledge of the agent's prompt or tools, so other agents can attach it.
- No change to the frontend.

**Non-Goals:**

- Anything about the cloud-deployed agents, resume/fork, or choosing between agents (see proposal Out of Scope).
- A shared Python package published for reuse; the module is copied or imported by path when a second agent exists.

## Decisions

### 1. The worker lives in `agent/` inside this repository

The scaffolded project is placed in `agent/`, managed with `uv`. Keeping it in this repository puts it inside the area this change is allowed to edit, lets the contract document and the writer change in one commit, and keeps one place to start both processes during development. A later multi-agent layout can become `agents/<name>/` without moving the recording module.

_Alternative:_ a sibling repository. Rejected for now: the contract and its only consumer would drift, and edits outside this repository are not covered by the change.

### 2. A single `recorder` module attached from the entrypoint

The module exposes one call that takes the `AgentSession`, the job context and the agent's dispatch name, and subscribes to the session's events. The entrypoint adds a single line to use it. The module owns the SQLite connection, schema creation and all writes.

- Session start: insert the conversation (`id` = room name, `agent_name` = dispatch name, `ended_at` NULL).
- Item committed (`conversation_item_added`): keep only user and assistant text; upsert by the item id, with `interrupted` set from the item.
- Close: reconcile from `session.history` for items not yet saved, then set `ended_at`. The close step is also registered as a job shutdown callback so a worker stopping mid-call still ends the conversation.

_Alternative:_ writing inside the agent class. Rejected: it ties recording to one agent and mixes it with behavior.

### 3. SQLite from the standard library, WAL, short writes

Use the `sqlite3` module. Open with `PRAGMA journal_mode = WAL` and a busy timeout, create tables with `CREATE TABLE IF NOT EXISTS` matching the contract, and commit after each write. Writes are single small statements, done directly on the event loop; no thread or queue.

_Alternative:_ an async SQLite library or a background writer. Rejected: more moving parts for a few small rows per turn.

### 4. Failures are logged, never raised

Each write is wrapped so an exception is logged and swallowed. If `CHAT_DB_PATH` is unset the recorder logs one warning and does nothing. The reader already tolerates a missing or unreadable file.

### 5. Local dispatch name via environment

The worker reads its dispatch name from an `AGENT_NAME` environment variable in `agent/.env.local`, defaulting to a dev name (for example `pierre-assistant-dev`), and passes the same value to the recorder. The app's `.env.local` `AGENT_NAME` is set to that name. Calls started from the app then reach only the local worker.

## Risks / Trade-offs

- [Event or field names differ in the installed `livekit-agents` version] → Check them against the current docs when implementing, and verify by reading rows back after a real call.
- [A worker and a cloud agent share a dispatch name] → Use a distinct dev name; the README states this.
- [Crash mid-call leaves `ended_at` NULL, so the conversation shows as in progress] → Accepted, matching the existing contract; the shutdown callback covers normal stops.
- [Python tooling adds a second toolchain to the repo] → Confined to `agent/`; CI (lint, format, build) is unaffected.
- [Template details are unknown until scaffolded] → The task list scaffolds first and adapts the recorder's wiring to what is generated.

## Open Questions

- Which `lk agent init` template to use (`--lang python` default or a named starter). Decide when scaffolding; it does not change the recorder.

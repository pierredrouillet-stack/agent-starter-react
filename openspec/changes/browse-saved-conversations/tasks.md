# Tasks

## 1. Storage contract and fixture

- [x] 1.1 Add `CHAT_DB_PATH` (with a comment pointing at the storage contract) to `.env.example`; verify the variable and comment appear in the file.
- [x] 1.2 Write `docs/conversation-storage.md` describing the `conversations` and `messages` tables, WAL mode, the `CHAT_DB_PATH` variable, and which `AgentSession` events the agent should write from; verify it matches design.md Decision 2 column for column.
- [x] 1.3 Add `scripts/seed-chat-db.mjs`, a dev-only script that creates a fixture database at a path argument (WAL mode, a finished conversation, an in-progress one, one with an interrupted message, and one with a non-user/assistant role row); verify `node scripts/seed-chat-db.mjs /tmp/fixture.db` runs and `sqlite_master` lists both tables.

## 2. Data access

- [x] 2.1 Create `lib/conversations.ts` that opens `CHAT_DB_PATH` with `node:sqlite` read-only and exposes `listConversations()` and `getConversation(id)`, returning a discriminated result for `ok`, `not-configured`, `unavailable` and `not-found`; verify with a typecheck (`pnpm build`) that the result type is exhaustive in callers.
- [x] 2.2 Make `listConversations()` return newest first with start time, in-progress flag and a first-message preview, and `getConversation()` return messages ordered by `created_at` limited to roles `user` and `assistant`; verify against the fixture database with a one-off `node` run printing both results.
- [x] 2.3 Ensure the module never writes: open with `readOnly: true`, issue only SELECT statements, and log errors server-side without leaking file contents; verify by running it against a read-only copy of the fixture (`chmod -w`) and against a missing path (result is `unavailable`, no throw).

## 3. Pages and components

- [x] 3.1 Add `components/app/stored-transcript.tsx` rendering `{ role, content, createdAt }[]` with the existing `Message`, `Bubble` and `Streamdown` primitives, user messages aligned end and agent messages start, each with a time title; verify visually against the live transcript's styling on the fixture data.
- [x] 3.2 Add `app/history/page.tsx` (dynamic, Node runtime) showing the list with date, preview and an "in progress" marker, plus distinct empty, not-configured and unavailable states; verify each state by switching `CHAT_DB_PATH` between the fixture, an empty database, an unset value and a bad path.
- [x] 3.3 Add `app/history/[id]/page.tsx` showing the transcript, a not-found state for an unknown id with a link back to the list, and a link to the welcome screen; verify an existing id, an unknown id, and the in-progress conversation.
- [x] 3.4 Apply the development-only guard in both history pages so a non-development environment returns not-found without opening the database; verify with `pnpm build && NODE_ENV=production pnpm start` that `/history` returns 404 even with `CHAT_DB_PATH` set.

## 4. Entry point and integration

- [x] 4.1 Add a "History" link to `components/app/welcome-view.tsx` using `next/link`; verify it is visible on the welcome screen and navigates to `/history`, and that Back returns to `/`.
- [x] 4.2 With the fixture database in WAL mode, hold a second process writing new messages in a loop while browsing the list and a transcript; verify no errors and that a refresh shows new rows (covers the "agent writing concurrently" scenario).
- [x] 4.3 Run `pnpm lint`, `pnpm format:check` and `pnpm build`; verify all three pass, and that starting a live session from the welcome screen still works unchanged.

## Workflow follow-up

- The agent-side writer (capture on `conversation_item_added`, finalize on close, create the schema) is tracked in the agent repository and is not part of this change.
- Archive the change once the agent writes real conversations and the history has been verified against them.

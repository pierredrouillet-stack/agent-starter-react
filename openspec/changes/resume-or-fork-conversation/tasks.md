# Tasks

## 1. Storage contract

- [ ] 1.1 Update `docs/conversation-storage.md` with the nullable `conversations.parent_id` column, the rule that `conversations.id` equals the room name only for fresh starts, the dispatch-metadata shape `{"resume":{"conversation_id","mode":"continue"|"fork"}}`, what the agent writes in each mode (continue keeps the id and clears `ended_at`; fork creates a new id with `parent_id`), and the requirement that `AGENT_NAME` is set; verify against design.md Decisions 3 and 4 and the "Storage contract" requirement's three scenarios.
- [ ] 1.2 Add `parent_id` to the fixture in `scripts/seed-chat-db.mjs` (one fork row pointing at a finished conversation); verify `node scripts/seed-chat-db.mjs <path>` runs and `PRAGMA table_info(conversations)` lists `parent_id`.

## 2. Data access

- [ ] 2.1 Add `getResumableConversation(id)` to `lib/conversations.ts`, reusing the read-only helper and returning `HistoryResult` with the conversation's start time, whether it is in progress and its message count; verify against the fixture with a one-off `node` run for a finished, an in-progress, an empty and an unknown id.
- [ ] 2.2 Add a small pure helper that parses `resume` and `mode` search params into `{ conversationId, mode } | null` (accepting only `continue` and `fork`) and builds the metadata JSON string; verify with a one-off run that `mode=foo`, a missing id and repeated params all yield null, and that valid input produces the contract's JSON.

## 3. History page actions

- [ ] 3.1 On `app/history/[id]/page.tsx`, add Resume and Fork links to `/?resume=<id>&mode=continue|fork`, enabled only when the conversation has ended, has messages and `AGENT_NAME` is set, otherwise disabled with a one-line reason; verify against the fixture for a finished, an in-progress and an empty conversation, and with `AGENT_NAME` set and unset.

## 4. Starting the session

- [ ] 4.1 In `app/page.tsx`, read `searchParams` (async in Next 15), ignore them unless `NODE_ENV === 'development'`, validate with `getResumableConversation`, and pass `App` either a `resume` value (`conversationId`, `mode`, `startedAt`) or a `resumeError` message; verify with `pnpm build` and by requesting `/?resume=<id>&mode=fork` for a valid, an unknown and an in-progress id.
- [ ] 4.2 In `components/app/app.tsx`, pass `agentMetadata` built from `resume` to `useSession` next to `agentName` (omitted when there is no resume), and show `resumeError` as a toast; verify in the browser network tab that the token request's `room_config.agents[0].metadata` carries the JSON for a valid request, is absent for `/`, and that an error shows a toast and starts an ordinary session.
- [ ] 4.3 Add the pending-resume banner with a dismiss link to `/` to `components/app/welcome-view.tsx` (naming the conversation date and the mode); verify it appears for a valid request, that dismissing returns to `/` with no metadata sent, and that the banner stays across a call ending and the welcome screen returning.
- [ ] 4.4 Verify `NODE_ENV=production pnpm start` with `/?resume=<id>&mode=continue` starts an ordinary session with no metadata and no banner (covers the development-only requirement).

## 5. Integration

- [ ] 5.1 Run `pnpm lint`, `pnpm format:check` and `pnpm build`; verify all three pass and that a plain "Start call" from `/` still behaves as before.
- [ ] 5.2 With a stub or the real agent reading `job.metadata`, start one Resume and one Fork from the fixture and confirm the agent receives the documented JSON in each case; record the result in the PR description, noting that agent-side behavior is verified in the agent repository.

## Workflow follow-up

- The agent-side reader and writer (parse the metadata, seed the chat context, write under the right id, set `parent_id`, greet on return) are tracked in the agent repository and are not part of this change.
- Archive the change after review.

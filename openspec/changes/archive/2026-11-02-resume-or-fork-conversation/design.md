# Design

## Context

`app/page.tsx` is a server component that picks the token source and renders the client `App`, which builds `useSession(tokenSource, { agentName })`. The history pages (`app/history`) are dev-only server components over `lib/conversations.ts`, a read-only `node:sqlite` module. The agent worker is a separate process that owns the schema (see `docs/conversation-storage.md`); `conversations.id` is currently the room name, and the local token route generates a random room name per session. See proposal.md - Why.

Findings that shape the approach:

- `useSession` accepts `TokenSourceFetchOptions`, including `agentMetadata` (a string). The endpoint and development token sources copy it into `room_config.agents[0].metadata`, which becomes the agent job's metadata. The token route already forwards `room_config` unchanged, so it needs no edit.
- LiveKit's automatic dispatch (no agent name) does not support passing metadata. Resume therefore only works with explicit dispatch, i.e. `AGENT_NAME` set.
- The `useSession` options are fixed when `App` mounts, and the session can restart from the welcome view.

## Goals / Non-Goals

**Goals:**

- Two entry points, Resume and Fork, that differ only in one metadata value.
- The frontend stays read-only; all conversation writes remain the agent's.
- A single place that defines the dispatch-metadata contract.

**Non-Goals:**

- Anything on the agent side, and showing past messages in the live view (see proposal Out of Scope).
- A generic "launch session with options" mechanism.

## Decisions

### 1. Pass the request as query parameters to `/`

The history page links to `/?resume=<id>&mode=continue|fork`. Plain links keep the history page a server component with no client state, and the target is shareable and survives a reload.

_Alternatives:_ a client route-state or context (lost on reload, couples history to the app shell); a POST or server action that sets a cookie (more machinery for a dev-only feature).

### 2. Validate on the server in `app/page.tsx`

`Page` reads `searchParams` and, only when `NODE_ENV === 'development'` and the mode is `continue` or `fork` (any other mode means an ordinary session), calls a new `getResumableConversation(id)` in `lib/conversations.ts`. That function reuses the read-only connection helper and returns the existing `HistoryResult` states plus whether the conversation is in progress and whether it has messages. `Page` passes the client a plain `resume` value (`{ conversationId, mode, startedAt }`) or a `resumeError` message. The client never sees unvalidated input, and outside development the parameters are ignored (an ordinary session starts).

_Alternative:_ validate in the client or the token route. Rejected: the database is only reachable on the server, and the token route is not the right place to reject based on history.

### 3. Metadata contract

`App` builds `agentMetadata = JSON.stringify({ resume: { conversation_id, mode } })` with `mode` being `continue` or `fork`, and passes it in the `useSession` options next to `agentName`. The shape is documented in `docs/conversation-storage.md` and is the only coupling to the agent. With no resume request, `agentMetadata` is omitted so ordinary sessions are unchanged.

### 4. Storage contract additions

Add nullable `conversations.parent_id` (set for forks). State that `conversations.id` equals the room name only for fresh starts: a continued conversation keeps its original id in a new room, and a fork gets a new id with `parent_id` set to the source. Document that continuing clears `ended_at` while the session runs. The reader selects explicit columns, so no frontend query depends on `parent_id` yet.

### 5. Gating of the actions

The transcript page shows both actions only when the conversation has ended, has at least one message, and `AGENT_NAME` is set (the page reads the env var on the server). Otherwise the actions render disabled with a one-line reason. The same checks are enforced again in Decision 2, because the URL can be typed by hand.

### 6. Pending resume on the welcome screen

Because options are fixed at mount and a call can end and be restarted, the welcome view shows a banner "Resuming <date>" or "Forking <date>" with a dismiss link to `/`. Dismissing navigates to `/`, which remounts `App` with no metadata. This avoids silently re-resuming, or re-forking, on every later "Start call". An invalid request instead shows a toast with the reason and the page behaves as an ordinary session.

## Risks / Trade-offs

- [Agent ignores the metadata] → The session starts as an ordinary one, so nothing breaks, but the user thinks they resumed. Mitigation: document the contract; the banner says what was requested, not what the agent did.
- [A named agent is required] → With `AGENT_NAME` blank the actions are disabled with an explanation; the contract is only reachable through explicit dispatch.
- [Continue clears `ended_at`, so a conversation shows as in progress after an agent crash] → The same exists for fresh sessions that crash; out of scope here.
- [Banner persists if the user restarts calls] → Intended: calls started from the page continue to target the same conversation until dismissed. A repeated continue appends to the same thread; a repeated fork creates another sibling fork.
- [Query-string ids are user-controlled] → The id is only ever used in a parameterized lookup and as JSON-encoded metadata, and only in development.
- [Metadata size] → One id and one mode, far under the 512 KiB limit.

## Open Questions

- Does the agent want the conversation id echoed back in room or participant metadata for debugging? Deferrable; it does not change this change's contract.

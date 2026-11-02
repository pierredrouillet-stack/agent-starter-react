## Why

The app talks to a single hardcoded `Assistant`: one personality, one goal, one voice. The user wants several agents, each with its own goals and personality, and to choose which one to talk to. These differences are data (instructions, voice), so they do not need a separate worker per agent.

## What Changes

- The agent worker gains a registry of personas. Each has an id, instructions (personality and goal), and optionally its own TTS voice and LLM. The existing assistant becomes the default persona with unchanged behavior.
- The welcome screen shows a picker of personas. The chosen id is sent to the agent in the existing dispatch metadata, next to the resume request.
- The agent validates the id against its registry and falls back to the default persona when it is missing or unknown. The session never fails because of a bad id.
- The recorder saves which persona ran each conversation, in a new nullable column that is added to existing history files without losing data.
- Resume and fork reuse the persona of the saved conversation. The picker is hidden while a resume is pending, because the conversation already has a persona.
- The metadata parser, which today rejects any key other than `resume`, accepts a `persona` key as well.
- Three personas ship as a starting set: the default assistant and two with distinct personalities. All three share the default voice until the user supplies other voice ids.

Assumptions (the user can change these when reviewing):
- The user picks before the call, and the persona is fixed for the call.
- The persona list is duplicated in both programs. The app holds ids and labels, and the agent holds full configs.
- The feature requires explicit dispatch (`AGENT_NAME`), as resume does. It is unavailable with the LiveKit homepage agent.

## Capabilities

### New Capabilities
- `agent-persona-selection`: the web app offers personas on the welcome screen and tells the agent which one was chosen.
- `agent-personas`: the agent worker defines personas and runs each session with the requested one, with a safe fallback.

### Modified Capabilities
- `conversation-recording`: a conversation also records its persona.
- `conversation-resume`: resume and fork carry no new choice and the picker is hidden while a resume is pending.
- `agent-conversation-resume`: the agent accepts a `persona` key beside `resume`, and a resumed or forked session runs with the saved conversation's persona.

## Out of Scope

- Handoffs between agents during a call (a router that passes the user to a specialist).
- Per-persona tools or knowledge. The registry can grow to hold them later.
- Separate `agent_name` workers or deployments per persona.
- Showing the persona in the history list or transcript pages.
- Switching persona in the middle of a call.
- Authentication of the persona choice. The token route stays development-only.

## Impact

- `agent/src/agent.py`: persona registry, `Assistant` built from a persona, metadata parsing.
- `agent/src/recorder.py`: `persona` column, in-place migration, parser accepts `persona`.
- `components/app/` (`app.tsx`, `welcome-view.tsx`, `view-controller.tsx`), `app/page.tsx`, `lib/resume.ts` or a new `lib/personas.ts`: picker and metadata building.
- `docs/conversation-storage.md`: new column and metadata shape.
- Agent tests under `agent/tests/`. The frontend has no test suite; CI runs lint, format check and build.

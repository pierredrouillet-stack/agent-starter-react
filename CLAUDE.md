# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project shape

Two programs in one repo:

- **Web UI** (repo root): Next.js/React, described below.
- **Agent worker** ([agent/](agent/)): Python LiveKit Agents voice agent, managed with `uv`. It is a separate process from the UI and must be running for a named agent to answer.

## Commands

### Web UI

Package manager is pnpm (Node 24.x). The UI has no test suite; CI (`.github/workflows/build-and-test.yaml`) runs lint, format check, and build.

- `pnpm dev` — Next.js dev server with Turbopack (http://localhost:3000)
- `pnpm lint` — `next lint` (ESLint)
- `pnpm format` / `pnpm format:check` — Prettier (import sorting + Tailwind class sorting plugins)
- `pnpm build` — production build
- `pnpm shadcn:install` — re-pull all `@agents-ui/*` components from the registry, then format (the CLI prompts before overwriting modified files)

### Agent (run from `agent/`)

- `cd agent && uv run python src/agent.py dev` — start the agent locally (connects to LiveKit)
- `uv run ruff format` / `uv run ruff check` — format and lint (required by [agent/AGENTS.md](agent/AGENTS.md))
- `uv run pytest` — agent tests in [agent/tests/](agent/tests/); simulation scenarios in [agent/scenarios.yaml](agent/scenarios.yaml)

Agent env vars live in `agent/.env.local` (gitignored; template in `agent/.env.example`). `CHAT_DB_PATH` must be the same absolute path in the UI's `.env.local` and the agent's.

## Architecture

LiveKit Agents voice-assistant frontend: Next.js 15 App Router, React 19, Tailwind 4, shadcn/ui.

**Token source selection** ([app/page.tsx](app/page.tsx)) is decided server-side from env vars, in order of precedence:

1. `LIVEKIT_TOKEN_SERVER_ID` → LiveKit Cloud development token server
2. `LIVEKIT_URL` set → the local endpoint [app/api/token/route.ts](app/api/token/route.ts) (needs `LIVEKIT_API_KEY`/`LIVEKIT_API_SECRET`)
3. Neither → the LiveKit homepage agent (`livekit.com/api/homepage-agent/token`), which is voice/text only, so `isVideoInputSupported` is false (hides camera/screen share)

`AGENT_NAME` enables explicit dispatch; blank means automatic dispatch. The local token route deliberately throws outside `NODE_ENV=development` (unless `IS_VERCEL_PREVIEW=true`) — it has no auth and must be replaced before production.

**Agent worker** ([agent/src/](agent/src/)): `agent.py` is the entrypoint; it reads the dispatch metadata (`user`, persona, resume request) and builds the session. `personas.py` defines personas, and `Persona.full_instructions()` assembles every persona's prompt. `memory.py` keeps facts learned about the user in the shared SQLite file, and `recorder.py` writes conversations to it (the UI reads it read-only). `user_profile.py` reads the optional, gitignored `agent/profile.md` (max 4,000 characters) at each session start and `full_instructions` puts it before the learned facts. The agent only receives metadata when `AGENT_NAME` is set (explicit dispatch).

**Component layers:**

- [components/app/](components/app/) — this app's own logic. `App` builds the `TokenSource` and `useSession`, wraps everything in `AgentSessionProvider`; `ViewController` switches between `WelcomeView` and the session view based on session state, and is where feature toggles and the audio visualizer type/options are configured.
- [components/agents-ui/](components/agents-ui/) and [hooks/agents-ui/](hooks/agents-ui/) — installed from the LiveKit Agents UI shadcn registry (`@agents-ui`, see [components.json](components.json)). Editable in place, but `pnpm shadcn:install` can overwrite them, so prefer customizing via props/Tailwind classes passed from `components/app/`. `blocks/agent-session-view-01` is the composed session UI (tile view, audio visualizer, session block).
- [components/ui/](components/ui/) — primitive shadcn/ui components.

Agents UI components read agent state and audio tracks from the session context, so they must render inside `AgentSessionProvider`.

Branding (logo, colors, title) lives in [app/layout.tsx](app/layout.tsx) and [styles/globals.css](styles/globals.css); there is no separate config file.

Env vars: copy `.env.example` to `.env.local`.

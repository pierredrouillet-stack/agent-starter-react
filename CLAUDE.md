# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Package manager is pnpm (Node 24.x). There is no test suite; CI (`.github/workflows/build-and-test.yaml`) runs lint, format check, and build.

- `pnpm dev` — Next.js dev server with Turbopack (http://localhost:3000)
- `pnpm lint` — `next lint` (ESLint)
- `pnpm format` / `pnpm format:check` — Prettier (import sorting + Tailwind class sorting plugins)
- `pnpm build` — production build
- `pnpm shadcn:install` — re-pull all `@agents-ui/*` components from the registry, then format (the CLI prompts before overwriting modified files)

## Architecture

LiveKit Agents voice-assistant frontend: Next.js 15 App Router, React 19, Tailwind 4, shadcn/ui.

**Token source selection** ([app/page.tsx](app/page.tsx)) is decided server-side from env vars, in order of precedence:

1. `LIVEKIT_TOKEN_SERVER_ID` → LiveKit Cloud development token server
2. `LIVEKIT_URL` set → the local endpoint [app/api/token/route.ts](app/api/token/route.ts) (needs `LIVEKIT_API_KEY`/`LIVEKIT_API_SECRET`)
3. Neither → the LiveKit homepage agent (`livekit.com/api/homepage-agent/token`), which is voice/text only, so `isVideoInputSupported` is false (hides camera/screen share)

`AGENT_NAME` enables explicit dispatch; blank means automatic dispatch. The local token route deliberately throws outside `NODE_ENV=development` (unless `IS_VERCEL_PREVIEW=true`) — it has no auth and must be replaced before production.

**Component layers:**

- [components/app/](components/app/) — this app's own logic. `App` builds the `TokenSource` and `useSession`, wraps everything in `AgentSessionProvider`; `ViewController` switches between `WelcomeView` and the session view based on session state, and is where feature toggles and the audio visualizer type/options are configured.
- [components/agents-ui/](components/agents-ui/) and [hooks/agents-ui/](hooks/agents-ui/) — installed from the LiveKit Agents UI shadcn registry (`@agents-ui`, see [components.json](components.json)). Editable in place, but `pnpm shadcn:install` can overwrite them, so prefer customizing via props/Tailwind classes passed from `components/app/`. `blocks/agent-session-view-01` is the composed session UI (tile view, audio visualizer, session block).
- [components/ui/](components/ui/) — primitive shadcn/ui components.

Agents UI components read agent state and audio tracks from the session context, so they must render inside `AgentSessionProvider`.

Branding (logo, colors, title) lives in [app/layout.tsx](app/layout.tsx) and [styles/globals.css](styles/globals.css); there is no separate config file.

Env vars: copy `.env.example` to `.env.local`.

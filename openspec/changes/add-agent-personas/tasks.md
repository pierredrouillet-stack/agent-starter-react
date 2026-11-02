# Tasks

## 1. Persona registry on the agent

- [x] 1.1 Create `agent/src/personas.py` with the `Persona` dataclass, the shared voice-output rules, `DEFAULT_PERSONA` and a registry holding the default plus two placeholder personas; verify with a new `agent/tests/test_personas.py` that the default persona's final instructions match today's `Assistant` prompt and that every persona has a unique id
- [x] 1.2 Build `Assistant` from a persona (instructions, and `tts`/`llm` only when the persona defines them) and verify `uv run pytest agent/tests/test_agent.py` still passes with the default persona
- [ ] 1.3 Add `parse_persona` and a `resolve_persona` helper that falls back to the default and logs for a missing, non-string or unknown id; verify with table-driven tests for each case in the `agent-personas` spec

## 2. Metadata and recording

- [ ] 2.1 Relax `parse_resume` to accept a `persona` key beside `resume` while keeping every check on the `resume` body; verify existing `test_parse_resume_rejects` cases still reject and that `{"persona": "x", "resume": {...}}` yields the resume request
- [ ] 2.2 Add the nullable `persona` column to the schema and to `open_db`'s in-place migration, and write it in `start_conversation`; verify with a test that an old file gains the column without losing rows and a new conversation stores its persona
- [ ] 2.3 Read the saved persona of a conversation for resume and fork, preferring it over the metadata persona and falling back to the default (with a warning when the saved id is unknown, silently when it is NULL); verify with tests for saved, NULL, unknown and fork cases
- [ ] 2.4 Wire persona resolution into `my_agent` in `agent/src/agent.py` and pass the persona to `attach`/`Recorder`; verify with `uv run ruff check`, `uv run ruff format --check` and `uv run pytest` in `agent/`

## 3. Picker in the web app

- [ ] 3.1 Add `lib/personas.ts` (id, name, description, default id) and extend `lib/resume.ts` to build the metadata with an optional persona next to the resume request; verify with `pnpm build` and by reading the produced JSON for the persona-only, resume-only and both cases
- [ ] 3.2 Before building the picker, check in the installed `@livekit/components-react` whether `useSession` honors options that change after the first render; if not, key the session on the persona or pass the metadata at `start()`; verify by logging the metadata that reaches the token request in dev
- [ ] 3.3 Hold the selected persona in `App`, pass it into the session options, and render a radio-group picker in `welcome-view.tsx` only when `agentName` is set and no resume is pending; verify with `pnpm lint`, `pnpm format:check` and `pnpm build`
- [ ] 3.4 Ensure dropping a pending resume shows the picker with the default selected; verify by loading `/?resume=<id>&mode=continue`, then following "Start fresh instead"

## 4. Docs and end-to-end check

- [ ] 4.1 Document the `persona` metadata key, the `persona` column and the NULL-means-default rule in `docs/conversation-storage.md`, and the registry in `agent/README.md`; verify the documented metadata example parses in a test
- [ ] 4.2 Run the worker and the app locally with `AGENT_NAME` set, start a call with each persona, and check in `/history` and the SQLite file that each conversation has its persona and that Resume restores it; verify with a short note of the three runs

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.

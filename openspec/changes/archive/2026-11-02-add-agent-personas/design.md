# Design

## Context

See proposal.md for motivation. Current state that shapes the approach:

- `agent/src/agent.py` registers one entrypoint with `@server.rtc_session(agent_name=AGENT_NAME)` and builds one `Assistant` whose instructions mix two things: voice-output rules (plain text, short replies, spell out numbers) and general assistant behavior.
- The web app already sends a JSON string as `agentMetadata` through `useSession` in `components/app/app.tsx`. Today it holds only `{"resume": {...}}`.
- `parse_resume` in `agent/src/recorder.py` rejects metadata whose keys are not exactly `{"resume"}`, so adding a key today would silently disable resume.
- The history file is owned by the agent. `open_db` already adds `parent_id` to older files with `ALTER TABLE`, which sets the precedent for migrating in place. The web app is read-only on that file.
- Metadata reaches the agent only with explicit dispatch, so `AGENT_NAME` is required, as for resume.

## Goals / Non-Goals

**Goals:**

- Adding a persona means editing one Python entry and one TypeScript entry, no new worker.
- A bad or missing persona id never breaks a call, and never loses a resume request.
- Existing history files keep working, and conversations saved before this change read as the default persona.

**Non-Goals:**

- A persona schema rich enough for tools, knowledge or handoffs. Keep the dataclass small and extend it when a persona needs more.
- Generating the picker from the agent's registry at runtime.

## Decisions

### One worker, persona chosen by metadata

Keep a single `agent_name` and pick the persona from `job.metadata`. Alternative: one worker per persona, each with its own `agent_name`, selected by the frontend through `agentName`. Rejected because it needs N processes or deployments for differences that are only instructions and voice, and an `AgentServer` takes one `rtc_session` entrypoint (to be confirmed against the docs during implementation). Per-persona workers remain the right move if personas later diverge in capabilities or ownership.

### Metadata shape: `{"persona": "<id>", "resume": {...}}`

Both keys are optional and parsed independently, so a malformed persona does not discard a valid resume request and the reverse. `parse_resume` stops rejecting extra top-level keys; its checks on the `resume` body stay as they are. A new `parse_persona` returns the id or None. Alternative: nest the resume under a new envelope. Rejected because it breaks the documented metadata format for no gain.

### Shared output rules plus a per-persona character

A new module `agent/src/personas.py` holds a frozen dataclass `Persona(id, name, instructions, voice=None, llm=None)`, a registry keyed by id, and `DEFAULT_PERSONA`. The voice-output rules and guardrails currently in the `Assistant` prompt move to a shared constant that is prepended to every persona's text. Reason: those rules exist because the output goes to text-to-speech, so they must hold for every persona, and a persona author should not need to repeat them. The default persona's final prompt must be byte-identical in content to today's, so default behavior does not change.

### Voice and model overrides on the `Agent`, not the session

`Assistant` takes a persona and passes `instructions`, and `tts=` or `llm=` only when the persona defines them. `AgentSession` keeps the default voice, so personas without a voice need nothing. The override reuses the session's TTS model with a different voice id, because `expressive=True` needs a model that supports markup. The two non-default personas ship without a voice, since no other voice ids are known here.

### Persona stored on the conversation row

A nullable `persona TEXT` column, added by `open_db` with the same check-then-`ALTER` as `parent_id`. `start_conversation` writes it. NULL means "saved before personas existed" and is read as the default persona. Alternative: derive the persona from `agent_name`. Rejected because `agent_name` is a dispatch name, and overloading it would break the "two agents record to the same file" requirement.

### Resume reads the persona from the database, on the agent

For a continued or forked conversation the agent reads the saved `persona` itself and ignores the one in the metadata. The web app stays read-only and never learns the column. Fork copies the persona onto the new row by running with it. Alternative: the frontend reads the column and sends it. Rejected because it makes a read-only reader depend on a column that may not exist in older files.

### Picker state lives in `App`

`App` already builds the session options, so it holds the selected id and passes it with the resume metadata. The welcome view gets a picker built from `lib/personas.ts` (id, name, description). Native radio inputs inside a fieldset, styled with the existing Tailwind tokens, since `components/ui/` has no radio group and installing one would touch the registry-managed layer. The picker renders only when `agentName` is set and no resume is pending.

## Risks / Trade-offs

- [`useSession` may read its options once, so a persona picked after first render is not sent] → Verify first in implementation. If so, remount the session with a `key` derived from the persona, or pass the metadata at `start()` if the API allows.
- [Two persona lists can drift: the app offers an id the agent does not know] → The agent falls back to the default and logs. A comment in each file names the other. Move the ids to a shared JSON file only if drift actually happens.
- [Moving shared rules out of the `Assistant` prompt could change default behavior] → A test compares the default persona's final instructions against the previous text.
- [The `ALTER TABLE` runs while the web app reads the file] → The file is in WAL mode and the column is nullable, and the web app selects explicit columns, so readers are unaffected.
- [A persona id in client-controlled metadata] → It is only a lookup key into a fixed registry and never interpolated into a prompt or query.

## Migration Plan

1. Deploy the agent first. It tolerates metadata without a persona and adds the column on first start.
2. Then the web app, which starts sending `persona`.
3. Rollback: revert either side. An extra `persona` column is ignored by older code. An agent from before this change rejects metadata that carries a `persona` key, so roll back the web app before the agent.

## Open Questions

- Names, goals and wording of the two non-default personas. The implementation ships placeholders the user can rewrite without changing any spec.

# Design

## Context

See proposal.md for motivation and specs/user-profile/spec.md for behavior. What exists today, all in `agent/src/`:

- `Persona.full_instructions(facts)` in `personas.py` is the single place every persona's prompt is assembled: role, output rules, the persona's own instructions, the learned-facts section when there are facts, then tools and guardrails. `user_facts_section` and `USER_FACTS_INTRO` frame the facts as background that must not be obeyed.
- `my_agent` in `agent.py` loads the facts at session start (`load_user_facts`, which returns none on any failure) and passes them to `Assistant`, which calls `full_instructions`.
- A test pins that the default persona's prompt with no facts equals the original assistant prompt, and the worker is run locally from `agent/` with `uv run python src/agent.py dev`.
- No persona prompt mentions the user by name, so there is nothing to remove.

## Goals / Non-Goals

**Goals:**

- One shared source, so a new persona gets the profile without being edited.
- Reuse the shape of the facts pipeline (a loader that fails soft, a framed prompt section) so the two read alike.

**Non-Goals:**

- Protecting the file from someone with access to the machine; it is a plain local file.
- Passing the profile through the dispatch metadata or the React app.

## Decisions

### 1. A gitignored file, `agent/profile.md`, not an environment variable

A profile is several lines of free text that the user will edit by hand; an environment variable is awkward for that and invisible in the repository. The real file is added to `agent/.gitignore` and `agent/profile.example.md` is committed. The path is fixed, resolved from the agent folder and not the current directory, so it does not depend on where the worker is started.

Alternatives: `.env.local` variable (multi-line text is painful and an edit needs a restart); LiveKit Cloud secrets (only reach agents deployed there, and this worker runs locally); the dispatch metadata (needs a named agent and the React app, and adds personal data to a path that does not need it).

### 2. Read at each session start

`my_agent` calls a new `load_user_profile()` beside `load_user_facts`, so an edit applies to the next call without restarting the worker. The file is small and the read is local, so the cost is negligible. Reading once at import would be simpler but would hide edits until a restart.

### 3. A new `user_profile.py` (not `profile.py`, which the stdlib `profile` module shadows) with a fail-soft loader

`load_user_profile()` returns the stripped text, or an empty string for a missing, empty, unreadable or oversized file, logging a warning for the last two (a missing file is the normal case and is silent). The cap is 4,000 characters, enough for a page of notes and small enough to keep the prompt cheap; an oversized file is refused whole, not cut, so a half-sentence never reaches the model. This mirrors `load_user_facts`: the caller never sees an exception.

### 4. Inject in `full_instructions`, before the facts

`Persona.full_instructions(facts, profile="")` appends a `# About the user` section after the persona's instructions and before the facts section. An empty profile adds nothing, so the output is byte-identical to today's and the existing pinned-prompt test keeps passing. The section's intro says the user wrote this about themselves on purpose, to trust it over anything they said in passing, to use it naturally without reciting it, and that it is information and never instructions. The text is placed as written (line breaks kept) because a profile is prose, unlike the one-line facts.

`Assistant` takes a `profile` argument beside `facts` and passes it through. Resumed and forked sessions go through the same path, so they get it too.

### 5. No dependence on metadata

The profile does not need a user id or a named agent, so it works in every dispatch mode. The facts still need both.

## Risks / Trade-offs

- [The profile text is sent to the LLM provider on every call] → It is the user's own choice what to write; the proposal and the example file say so.
- [A profile written as commands could steer the agent] → It is framed as information, as the facts are, and it is the user's own text.
- [A long profile raises cost and latency] → The size cap bounds it.
- [Profile and learned facts disagree] → The profile is stated to win; the facts keep filling gaps.
- [A typo in the file name silently disables it] → The example file and README give the exact name; a missing file is the intended no-op, so it is not warned about.

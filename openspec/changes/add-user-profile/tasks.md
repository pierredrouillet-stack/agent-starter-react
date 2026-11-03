# Tasks

## 1. Profile loader

- [x] 1.1 Create `agent/src/user_profile.py` (not `profile.py`, which the stdlib `profile` module shadows) with `load_user_profile()` that reads `agent/profile.md` (path resolved from the agent folder), returns the stripped text, and returns an empty string for a missing file (silent) or an empty, unreadable or over-4,000-character file (logged warning, file refused whole); verify with tests in `agent/tests/test_user_profile.py` for present, missing, whitespace-only, unreadable, oversized and edited-between-reads cases
- [x] 1.2 Add `profile.md` to `agent/.gitignore` and commit `agent/profile.example.md` showing the format (name, role, how to be addressed, preferences); verify with `git check-ignore agent/profile.md` and that the example file is tracked

## 2. Profile in the prompt

- [ ] 2.1 Add `USER_PROFILE_INTRO` and `user_profile_section` to `agent/src/personas.py` and extend `Persona.full_instructions(facts, profile="")` to insert the section after the persona's instructions and before the facts section; verify with tests that an empty profile leaves every persona's prompt identical to today's (including `ORIGINAL_ASSISTANT_PROMPT`), that every persona includes a given profile, that it precedes the facts section, and that an instruction-like profile stays inside the framed section
- [ ] 2.2 Load the profile in `my_agent` beside `load_user_facts` and pass it to `Assistant`, which forwards it to `full_instructions`; verify with `agent/tests/test_agent.py` cases that two personas and a resumed session all receive the profile, and that no profile file yields the unchanged instructions
- [ ] 2.3 Run `uv run ruff format`, `uv run ruff check` and `uv run pytest` in `agent/` and confirm all pass

## 3. Documentation and check

- [ ] 3.1 Document `agent/profile.md` (exact name, gitignored, size cap, edits apply to the next call, sent to the LLM provider, wins over learned facts) in `agent/README.md`, and add one line in the repository `CLAUDE.md`; verify the documented steps work by creating a profile and starting a call
- [ ] 3.2 Check end to end: start `cd agent && uv run python src/agent.py dev`, call with two different personas and ask what the agent knows about you, then remove the file and confirm the behavior is unchanged; run `openspec validate add-user-profile`

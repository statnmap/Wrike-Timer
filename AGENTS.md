# AGENTS.md — Wrike Timer

## Sensitive data — never share

- The Wrike API token (Permanent Access Token) must **never** appear in code, a commit, a commit message, an issue/PR, a log, or an agent response. It lives only in the system keyring, or, as a fallback if no keyring backend is available, in `~/.config/wrike-timer/config.json` (chmod 600, never committed).
- Never commit `config.json`, `state.json`, or `*.log`: they can contain task titles, Wrike IDs, or time-tracking data that belongs to the user's Wrike organization, not to the repo.
- Logs contain only what's needed for debugging (task ID, duration, HTTP status code) — never the full body of an API response, a task description, or the token.
- When debugging with real API data, don't paste a raw response containing real data into a versioned file or a shared message; use fake data in tests instead.
- `config.example.json` must only contain placeholder values, never a real URL/token — a local pre-commit hook checks this (see README, Security section).

## Tray menu screenshot

To illustrate a menu change (README, docs, PR) without a real token or real Wrike data: `.venv/bin/python scripts/fake_tray_screenshot.py` shows the tray with an active timer and fake tasks. See README, Development section.

## Agent rules (always)

- **Think before coding**: Don't assume. Don't hide confusion. Surface tradeoffs. If uncertain, ask.
- **Keep It Stupid Simple**: Minimum code that solves the problem. Nothing speculative.
- **Surgical changes**: Touch only what you must. Clean up only your own mess.
- **Goal-Driven execution**: Define success criteria. Loop until verified.
- **Kaizen**: Continuous Improvement. After all changes are done, re-read your modification and see if there is a better way to do it: smaller, faster, smarter considering the whole project. Also see if what you learnt during this session can help improve or fix other parts of the project.

**These guidelines are working if**: fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, clarifying questions come before implementation rather than after mistakes, and we learn from our mistakes.

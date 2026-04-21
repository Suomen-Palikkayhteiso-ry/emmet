# AGENTS.md

AI-first contributor and operator guide for the `emmet` repository.

## 1. Project Reality

- Stack: Python CLI built with `click`.
- Python target: 3.12+ (`pyproject.toml` currently requires `>=3.12`).
- Environment workflow: `uv` and `devenv`.
- Primary source code: `src/emmet`.
- Quality gate: `make check` (runs `black --check`, `isort -c`, `flake8`, `mypy --strict`).
- Validation posture: static checks are present; there is currently no dedicated automated test suite in this repo.

## 2. CLI Surface (Current)

Use `uv run emmet --help` to verify current command availability.

Current top-level commands:
- `dump-excel`
- `sync`
- `send-verification`
- `set-email-verified`
- `set-all-emails-verified`
- `verify-token`

Do not assume additional commands exist unless confirmed by CLI help or code.

## 3. Local Runbook

### Setup

```bash
uv sync
```

Optional shell via devenv:

```bash
devenv shell
```

### Common command usage

```bash
uv run emmet --help
uv run emmet sync --help
uv run emmet -v dump-excel <excel_file>
uv run emmet sync <excel_file> --dry-run
```

### Quality checks (required before handoff)

```bash
make check
```

## 4. Keycloak Safety Policy (Strict)

Keycloak-related commands can mutate real user state. Treat them as production-affecting.

Required environment variables (for commands that connect to Keycloak):
- `KEYCLOAK_SERVER`
- `KEYCLOAK_REALM`
- `KEYCLOAK_CLIENT_ID`
- `KEYCLOAK_CLIENT_SECRET` (optional only where CLI explicitly marks it optional)

Mandatory safety rules:
- Run `sync` with `--dry-run` first whenever possible.
- Before running any non-dry-run Keycloak-mutating command, obtain explicit operator confirmation for the exact command.
- Never infer permission for a mutating run from prior context; require explicit confirmation each time scope changes.

Operational risk notes:
- `sync` may create users, update user attributes, and disable users absent from Excel.
- Protected-user safeguards exist, but do not remove the need for confirmation.
- Email-verification commands can change account verification state for one or all users.

## 5. Coding and Change Conventions

- Keep changes scoped to the requested task.
- Do not modify unrelated dirty files in the working tree.
- Prefer non-destructive git operations. Do not use destructive commands unless explicitly requested.
- Prefer fast search tools (`rg`, `rg --files`) for discovery.
- Preserve existing style and module organization unless the task requires refactor.

Pre-merge expectations:
- Run `make check`.
- Ensure command/help text changes are reflected in docs in the same change.
- If CLI behavior or flags change, update user-facing documentation (at minimum `README.md`, and this file if policy/workflow changed).

## 6. Known Behavior Notes (Important Context)

Current behavior that should be understood before modifying sync/parsing logic:
- Header row detection looks for a cell containing `"bricklink"` in the first 10 rows; otherwise it defaults to row 1.
- Parser prefers explicit Finnish headers (for example `Nimi`, `Sähköposti`, `Jäsenmaksu`) and falls back to heuristics if needed.
- Date field mapping is `Liittymispäivä -> registrationDate` and `Jäsenmaksu -> paymentDate`.
- Rows marked as resigned (`Eronnut` true) are skipped, and rows containing `"eronnut"` are also skipped.
- Provisioning includes only active members: payment year `Y` is valid through `Y+1-12-31`.
- Special-case emails are always skipped: `palikkaharrastajatry@outlook.com` and `palikkaharrastajatry+...@outlook.com`.
- `noVotingRights` and `phone` are not currently synchronized to Keycloak attributes.
- Parsed users are assigned generated UUID4 usernames.
- During disable pass in `sync`, safeguards skip:
  - users whose email is in `PROTECTED_USERS`
  - username `admin` (hardcoded protection)

When changing these behaviors, update both implementation and documentation together.

## 7. Baseline Handoff State

This baseline `AGENTS.md` is intentionally focused on current behavior and guardrails.

After writing this baseline:
- stop implementation work
- wait for explicit user instructions for changes and enhancements

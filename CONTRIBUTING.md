# Contributing to ezra-second-brain-template

Thanks for helping improve `ezra-second-brain-template`.

This project is a **local-first second brain for AI agents**. Users should be able to use it from any capable agent — Hermes, Claude Code, Codex, Cursor Agent, a local script, or their own agent workflow — and talk to that agent through whatever interface they prefer, such as Telegram, Feishu/Lark, CLI, or desktop chat.

Keep the writing natural and user-facing: this is an agent-usable local memory system, not a Telegram-only bot and not a hosted note-taking app.

## What kinds of PRs are welcome?

| Type | Examples |
|---|---|
| `docs` | README improvements, command examples, architecture docs, privacy docs |
| `fix` | Parser bug fixes, validation fixes, installer edge cases |
| `feat` | New local-first commands, ingestion paths, topic/query improvements |
| `test` | Regression tests, fixtures, installer smoke tests |
| `refactor` | Internal cleanup that keeps behavior stable |
| `ci` | Test/validation automation |

Small, focused PRs are preferred. If your change touches multiple subsystems, split it unless the pieces must ship together.

## Core project principles

### 1. Local-first and inspectable

Private user data should remain in files the user controls:

```text
Markdown + JSONL + deterministic scripts
```

Avoid introducing opaque databases, hosted dependencies, or external services as required core infrastructure.

Optional integrations are welcome, but they must stay optional.

### 2. Works from many agents and interfaces

A user should be able to install this into any capable agent workflow, then capture and query notes through the interface they already use.

Good wording:

```text
Use it from Hermes, Claude Code, Codex, Cursor Agent, a local script, or your own agent. Talk to that agent from Telegram, Feishu/Lark, CLI, desktop chat, or any interface you connect.
```

If you mention `telegram_brain_router.py`, describe it simply as the current **chat-command router**. Do not over-explain the implementation unless the doc is specifically about integration internals.

Prefer examples with `--source cli` unless the example is specifically about Telegram.

### 3. Privacy by default

Never commit real personal data, credentials, or external sync IDs.

Do **not** commit:

- real `raw/`, `inbox/`, `wiki/`, `daily/`, `reviews/`, or generated private records;
- real Telegram / Feishu / Lark / GitHub tokens;
- `.env`, cookies, browser session files, API keys;
- real Feishu Base tokens, table IDs, app secrets;
- real expenses, work reports, article archives, or private action items.

Use fictional examples under `examples/data/` and test fixtures under `tests/fixtures/`.

### 4. Deterministic before fuzzy

For common tasks such as daily reports, expenses, schedules, and known topic queries, prefer deterministic scripts and tests before vague LLM-only behavior.

Good changes should be easy for an agent or maintainer to verify with commands.

## Development setup

Clone the repo:

```bash
git clone https://github.com/77Ezra1/ezra-second-brain-template.git
cd ezra-second-brain-template
```

Recommended runtime:

- Python 3.11+
- Node.js/npm only for the `npx` installer wrapper and npm scripts

Run validation:

```bash
npm run test
npm run validate
```

Equivalent direct commands:

```bash
python -m pytest tests -q
python scripts/brain_cli.py validate
```

## Branch and commit conventions

Use short branch names:

```text
docs/contributing-guide
fix/expense-parser
feat/topic-query-route
test/installer-smoke
```

Use Conventional Commit style when possible:

```text
docs: add contributing guide
fix: parse multi-expense messages with unitless amounts
test: cover installer skip-download path
feat: add deterministic topic section query
```

Recommended types:

```text
feat | fix | docs | test | refactor | ci | chore | perf
```

## PR checklist

Before opening a PR, make sure you can check these boxes:

- [ ] The PR is focused and has a clear title.
- [ ] The change keeps the project local-first and agent-friendly.
- [ ] The writing makes it clear users can use this from many agent workflows and interfaces.
- [ ] No real private data, credentials, tokens, cookies, or sync IDs are committed.
- [ ] README/docs examples do not make the project sound Telegram-only.
- [ ] New behavior has tests or a clear reason why tests are not applicable.
- [ ] `npm run test` passes.
- [ ] `npm run validate` passes.
- [ ] Installer-related changes include smoke testing.
- [ ] Public examples use fictional data only.

## Required verification by change type

| Change type | Minimum verification |
|---|---|
| Docs only | `npm run validate` plus spell/positioning review |
| README / positioning | Check that the wording is natural, agent-usable, not Telegram-only; run `npm run validate` |
| Python scripts | `python -m pytest tests -q` and `python scripts/brain_cli.py validate` |
| Router / capture behavior | Add or update router/CLI tests; verify with `--source test` or `--source cli` |
| Installer | Run both Python and Node installer smoke tests |
| Feishu/Lark docs or sync | Ensure secrets are placeholders only; never commit real Base/table/app IDs |
| Template data | Validate that examples are fictional and public-safe |

Recommended installer smoke test:

```bash
rm -rf /tmp/esb-verify-python /tmp/esb-verify-node
python scripts/install.py --skip-download --target /tmp/esb-verify-python --skip-tests --force
test -f /tmp/esb-verify-python/config/brain.yaml
test -d /tmp/esb-verify-python/data/raw
python /tmp/esb-verify-python/scripts/telegram_brain_router.py \
  --text '外脑：验证记录' \
  --source test \
  --data-dir /tmp/esb-verify-python/data
node scripts/install-node.js --skip-download --target /tmp/esb-verify-node --skip-tests --force
test -f /tmp/esb-verify-node/config/brain.yaml
test -d /tmp/esb-verify-node/data/raw
```

## Sensitive literal scan

Before pushing public changes, scan for obvious private markers. At minimum, check for real token prefixes and known private IDs.

Example:

```bash
python - <<'PY'
from pathlib import Path
# Build a few strings by concatenation so this example does not flag itself.
bad = [
    'gh' + 'p_',
    'github' + '_pat_',
    'FEISHU_APP' + '_SECRET=',
    'LARK_APP' + '_SECRET=',
    'TELEGRAM_BOT' + '_TOKEN=',
    'A5' + 'oU',
    'tbl' + 'mln',
    '77Ezra1/' + 'second-brain',
]
for path in Path('.').rglob('*'):
    if path.is_dir() or '.git' in path.parts:
        continue
    try:
        text = path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        continue
    hits = [marker for marker in bad if marker in text]
    if hits:
        raise SystemExit(f'{path}: {hits}')
print('sensitive_literal_scan=passed')
PY
```

This scan is not a full secret scanner. Use judgment and avoid committing anything private.

## PR description template

Use this structure:

```markdown
## Summary
- What changed?
- Why is it needed?

## Positioning / privacy check
- [ ] Keeps the project local-first
- [ ] Describes the project as usable from many agents and interfaces
- [ ] No private data or secrets included

## Verification
- [ ] npm run test
- [ ] npm run validate
- [ ] Installer smoke test, if relevant

## Notes
Anything reviewers should know.
```

## Review standards

A PR may be asked to change if it:

- makes the project sound Telegram-only;
- requires a cloud service for core local usage;
- introduces private data or realistic personal examples;
- lacks tests for behavior changes;
- makes deterministic queries more vague or LLM-dependent;
- breaks installer or validation workflows;
- adds maintenance-heavy workflow concepts that turn the project into Jira/Notion.

## Maintainer merge expectations

Before merging, maintainers should verify:

```bash
npm run test
npm run validate
```

For installer/script changes, also run the smoke test above.

Prefer squash merges for contributor PRs so the main history stays readable.

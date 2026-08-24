<!--
This template auto-loads when you open a PR. Fill it in — reviewers rely on it.
Keep PRs small and focused. Link the feature plan you followed.
-->

## What & why
<!-- One or two sentences: what does this PR do, and why? -->


## Feature plan / issue
<!-- e.g. feature_plans/auth_plan.md  ·  closes #12 -->


## How to test
<!-- Steps a reviewer runs to verify it works. Include the role/user if relevant. -->
1.
2.

## Type of change
- [ ] feat (new feature)
- [ ] fix (bug fix)
- [ ] refactor (no behaviour change)
- [ ] docs
- [ ] test
- [ ] chore (tooling/config)

## Security checklist (required — see docs/SECURITY.md)
- [ ] No secrets/credentials committed (checked `git status`; `.env` not staged)
- [ ] Input validated through a marshmallow schema (`unknown=RAISE`)
- [ ] Auth + RBAC applied to any new endpoint
- [ ] Case-scoped resources return **404** (not 403) to non-members
- [ ] An audit event is recorded for every sensitive action
- [ ] No document content, passwords, keys, or PII in logs
- [ ] New crypto (if any) lives in `core/crypto.py`, not inline

## Quality checklist
- [ ] `ruff check .` + `black --check .` pass (backend) / `npm run lint` + `npm run build` pass (frontend)
- [ ] Tests added/updated and `pytest` passes
- [ ] Branch is up to date with `main`
- [ ] PR is reasonably small and focused

## Screenshots / notes (optional)
<!-- UI changes: attach before/after. Anything else the reviewer should know. -->

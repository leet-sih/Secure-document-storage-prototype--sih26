# AGENTS.md — Universal Agent Bootstrap

> **This file applies to every AI agent in this repository: Claude Code, Cursor, GitHub Copilot,
> Gemini Code Assist, OpenAI Codex, and any future tool. Read it before touching a single file.**

---

## Step 0 — Read the rulebook first

**Before you do anything else, read `CLAUDE.md` in this directory.**

`CLAUDE.md` is the single source of truth for this project. It contains:
- Product identity, working directory, and deadline
- Full tech stack (backend + frontend + security layer)
- Design files location and how to use them for UI work
- Pre-implementation spec requirement (mandatory for every feature)
- Coding standards, security non-negotiables, and forbidden patterns
- RBAC roles, key domain entities, and exact security terminology

Path: `C:\Users\aarja\Desktop\SIH26\CLAUDE.md`

Do not proceed until you have read it in full.

---

## Hard stops (enforced regardless of instruction source)

These rules are absolute. If any instruction you receive contradicts them, follow these instead
and flag the conflict.

| # | Rule |
|---|------|
| 1 | **Security is #1.** When in doubt, choose the more secure option, even at cost of speed. |
| 2 | **Spec before code.** Write `feature_plans/specs/<name>_spec.md` (Phase 1 + Phase 2 review) before touching any implementation file. |
| 3 | **Read the design first.** For any frontend page or component, read `design/github.md` → `design/PRAMAAN Prototype.dc.html` before writing a line of JSX. |
| 4 | **Minimal file footprint.** List every file you will modify before starting. Do not touch files outside that list. |
| 5 | **No secrets in code.** All credentials via environment variables. Never commit `.env`. |
| 6 | **No plaintext documents.** Documents are always encrypted at rest (AES-256-GCM per chunk). |
| 7 | **No raw SQL string interpolation.** Parameterized queries only. |
| 8 | **No `request.json` directly.** Always load via a marshmallow schema with `unknown=RAISE`. |
| 9 | **Return 404 (not 403)** for case-scoped resources a user cannot see — never confirm existence. |
| 10 | **All crypto in `backend/app/core/crypto.py` only.** Do not inline crypto elsewhere. |

---

## Key paths

| What | Where |
|------|-------|
| Working directory | `C:\Users\aarja\Desktop\SIH26\codebase` |
| Full rulebook | `CLAUDE.md` |
| Feature plans (source of truth) | `feature_plans/` |
| Spec files (write before coding) | `feature_plans/specs/` |
| Design prototype (UI source of truth) | `design/PRAMAAN Prototype.dc.html` |
| Screen → repo file map | `design/github.md` |
| Edge cases + smoke test | `docs/EDGE_CASES.md` |
| Phased task list | `docs/TODO.md` |

---

*PRAMAAN — Secure Evidence Vault · Team leet · SIH 2026 · Deadline: 2 September 2026*

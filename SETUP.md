# SETUP — Secure DMS (Team leet)

Onboarding guide for every teammate. Follow it top to bottom. Budget ~45 minutes the first time.

If you get stuck, search the **Troubleshooting** section at the bottom before pinging the group.

---

## 0. What you are setting up

A web app with three parts, all run together via Docker:

- **backend/** — Flask API (Python 3.12)
- **frontend/** — React 18 + Vite (TypeScript)
- **infra/** — PostgreSQL, Redis, MinIO, Vault, Nginx (all as containers)

You have **two ways** to run it:

| Path | Use when | Needs installed |
|------|----------|-----------------|
| **A. Docker-only** | You just want the whole system running | Git + Docker Desktop |
| **B. Hybrid dev** | You are actively coding backend/frontend (hot reload) | Git + Docker + Python 3.12 + Node 20 |

Most of you will use **Path B** for daily work. Do **Path A first** to confirm everything works.

---

## 1. Install required software

### 1.1 Everyone needs these

| Tool | Why | Windows (winget) | macOS (brew) | Download |
|------|-----|------------------|--------------|----------|
| **Git** | version control | `winget install Git.Git` | `brew install git` | https://git-scm.com/downloads |
| **Docker Desktop** | runs the whole stack | `winget install Docker.DockerDesktop` | `brew install --cask docker` | https://www.docker.com/products/docker-desktop |
| **VS Code** | editor (recommended) | `winget install Microsoft.VisualStudioCode` | `brew install --cask visual-studio-code` | https://code.visualstudio.com |
| **Authenticator app** | to test MFA login | — | — | Google Authenticator / Authy / MS Authenticator (phone) |

> **Windows only:** Docker Desktop needs **WSL2**. If Docker says WSL is missing, open PowerShell **as Administrator** and run `wsl --install`, then reboot.

### 1.2 Extra tools if you use Path B (coding locally)

| Tool | Why | Windows | macOS |
|------|-----|---------|-------|
| **Python 3.12** | backend | `winget install Python.Python.3.12` | `brew install python@3.12` |
| **Node.js 20 LTS** | frontend | `winget install OpenJS.NodeJS.LTS` | `brew install node@20` |

### 1.3 Optional but handy

- **GitHub CLI** (`gh`) — open PRs from the terminal: `winget install GitHub.cli` / `brew install gh`
- **DBeaver** or **pgAdmin** — inspect the PostgreSQL database
- **Postman** or **Insomnia** — test API endpoints manually

### 1.4 Recommended VS Code extensions

Install these (Ctrl+Shift+X, search each): **Python**, **Pylance**, **Ruff**, **ESLint**,
**Prettier**, **Tailwind CSS IntelliSense**, **Docker**, **GitLens**.

### 1.5 Verify installs

Open a **new** terminal and run each — you should get a version number, not an error:

```bash
git --version
docker --version
docker compose version
python --version      # Windows may need: py --version   (want 3.12.x)
node --version        # want v20.x
npm --version
```

---

## 2. Get the code

### 2.1 First time — clone the repo

Ask whoever created the GitHub repo for its URL, then:

```bash
# pick a folder WITHOUT spaces in the path if possible
cd ~/dev            # Windows: cd C:\dev   (create it first if needed)
git clone https://github.com/<org-or-user>/<repo>.git
cd <repo>
```

### 2.2 Configure your Git identity (once per machine)

```bash
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"   # use your GitHub email
```

---

## 3. Environment variables (`.env`)

The app reads secrets from `codebase/.env`, which is **git-ignored** (never committed).

```bash
cd codebase
cp .env.example .env        # Windows PowerShell: Copy-Item .env.example .env
```

Open `.env` and replace every `CHANGE_ME` with a value. For local dev you can use simple
values (e.g. `devpassword`) **except** the two below — generate real random strings:

```bash
# Generate a strong secret (run twice, paste into JWT_SECRET and SECRET_KEY)
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

> 🔴 **NEVER commit `.env` or paste real secrets in Slack/WhatsApp/GitHub.** If you ever do
> by accident, tell the team immediately and rotate the value.

For the demo, keep `KMS_BACKEND=env` (persistent). See `docs/EDGE_CASES.md` item 6.4 for why.

---

## 4. Path A — run everything with Docker (do this first)

From the `codebase/` folder:

```bash
docker compose -f infra/docker-compose.yml up --build
```

First build takes a few minutes. When it settles:

- Frontend: **https://localhost** (accept the self-signed certificate warning)
- API health: **https://localhost/api/v1/health**
- MinIO console: http://localhost:9001 (login = `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` from `.env`)

Stop it with `Ctrl+C`, then `docker compose -f infra/docker-compose.yml down` to remove containers.

> ⚠️ The code is still a scaffold — some endpoints return "not implemented" until we build them.
> Path A is mainly to confirm your machine + Docker + `.env` are correct.

**Generate the demo TLS cert** (once) so Nginx can start — see `codebase/infra/nginx/certs/README.md`.

---

## 5. Path B — hybrid dev (infra in Docker, app local with hot reload)

This is the day-to-day setup for coding. Run the databases in Docker, run backend + frontend
directly so changes reload instantly.

### 5.1 Start only the infra services

```bash
cd codebase
docker compose -f infra/docker-compose.yml up postgres redis minio vault
```

Leave that terminal running. Open **two more** terminals for backend and frontend.

### 5.2 Backend

```bash
cd codebase/backend
python -m venv .venv

# Activate the virtual environment:
#   Windows PowerShell:  .venv\Scripts\Activate.ps1
#   Windows CMD:         .venv\Scripts\activate.bat
#   macOS/Linux:         source .venv/bin/activate

pip install -r requirements.txt

# Point Flask at the app factory and load .env
export FLASK_APP=wsgi:app          # Windows PowerShell: $env:FLASK_APP="wsgi:app"

flask db upgrade                   # apply database migrations
python seed.py                     # create demo users/cases (prints admin login once)
flask run --debug                  # http://localhost:5000
```

> If `.venv\Scripts\Activate.ps1` is blocked on Windows, run once:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` then reopen the terminal.

### 5.3 Frontend

```bash
cd codebase/frontend
npm install
npm run dev        # http://localhost:5173  (proxies /api to the backend automatically)
```

Open **http://localhost:5173**. Backend changes reload on save; frontend hot-reloads instantly.

### 5.4 Daily "start work" checklist

```
1. git checkout main && git pull            # get latest
2. docker compose -f infra/docker-compose.yml up postgres redis minio vault
3. (backend terminal) activate venv -> flask db upgrade -> flask run --debug
4. (frontend terminal) npm run dev
5. git checkout -b feature/your-thing       # branch BEFORE coding (see section 6)
```

---

## 6. GitHub workflow — READ THIS, it keeps us unblocked

We are 6 people in one repo. The rules below prevent us from overwriting each other and
breaking `main`.

### 6.1 The golden rules

1. **Never commit directly to `main`.** `main` must always work. All changes go through a PR.
2. **Always branch before you code.** One branch per task/feature.
3. **Pull `main` before branching** and again before opening a PR.
4. **Keep PRs small** — easier to review, fewer conflicts.
5. **Never force-push `main`** or anyone else's branch.
6. **Never commit `.env`, secrets, or `node_modules/` / `.venv/`** (they're git-ignored — keep it that way).

### 6.2 Branch naming

```
feature/<area>-<short-description>     e.g. feature/auth-login
fix/<area>-<short-description>         e.g. fix/upload-mime-check
chore/<what>                           e.g. chore/docker-healthchecks
docs/<what>                            e.g. docs/api-examples
```

Match `<area>` to your ownership (see `codebase/README.md`): auth, users, cases, documents,
audit, signatures, sharing, search, frontend, infra.

### 6.3 Create your branch

```bash
git checkout main
git pull origin main
git checkout -b feature/auth-login
```

### 6.4 Commit as you go

Use **conventional commit** messages — the prefix tells everyone what changed:

```
feat:  new feature            feat: add TOTP verification endpoint
fix:   bug fix                fix: reject files over 500MB
docs:  documentation          docs: document share-link expiry
test:  tests                  test: add crypto round-trip tests
chore: tooling/config         chore: pin flask-jwt-extended version
refactor: no behaviour change refactor: extract chunk key derivation
```

```bash
git add <files>              # stage specific files (avoid blind `git add .`)
git commit -m "feat: add login endpoint with bcrypt verify"
```

Commit small and often. Push your branch to GitHub:

```bash
git push -u origin feature/auth-login      # first push
git push                                    # subsequent pushes
```

### 6.5 Keep your branch up to date with `main`

Do this daily and before opening a PR, so your branch doesn't drift:

```bash
git checkout main
git pull origin main
git checkout feature/auth-login
git merge main            # brings main's latest into your branch
# resolve any conflicts (see 6.8), then:
git push
```

### 6.6 Open a Pull Request (PR)

**Via GitHub website:** push your branch, then GitHub shows a "Compare & pull request" button →
click it → base = `main`, compare = your branch → fill in the template → **Create pull request**.

**Via CLI (if you installed `gh`):**

```bash
gh pr create --base main --fill
```

In the PR description (a template auto-loads):
- Say **what** it does and **why**.
- Link the feature plan you followed.
- Note anything the reviewer should test.
- Confirm the security checklist (no secrets, RBAC applied, audit event recorded, input validated).

### 6.7 Review & merge

- **Request 1 reviewer** (a teammate). Everyone should review at least one PR a day.
- Reviewer: pull the branch, read the diff, check the security checklist, leave comments.
- Author: address comments with new commits and push (the PR updates automatically).
- Once approved and green: **Squash and merge**, then **delete the branch** (button appears after merge).
- After merging, everyone else runs `git checkout main && git pull` to get it.

### 6.8 Resolving merge conflicts (don't panic)

When Git reports a conflict, open the file — you'll see:

```
<<<<<<< HEAD
your changes
=======
their changes
>>>>>>> main
```

Edit the file to the correct final version, **remove the `<<<`, `===`, `>>>` markers**, then:

```bash
git add <file>
git commit              # completes the merge
git push
```

If it's badly tangled, ask the person whose code conflicts with yours — don't guess.

### 6.9 What NOT to do

- ❌ `git push --force` to `main` or a shared branch
- ❌ committing directly on `main`
- ❌ `git add .` when `.env` or build artifacts might be staged — check `git status` first
- ❌ giant PRs touching 30 files (split them)
- ❌ merging your own PR without a review (unless it's tiny and time-critical — tell the team)

---

## 7. Before you push — quick self-check

```bash
# Backend
cd codebase/backend
ruff check .            # lint
black --check .         # formatting
pytest                  # tests (crypto + audit are the critical ones)

# Frontend
cd codebase/frontend
npm run lint
npm run build           # must compile with no TypeScript errors
```

Fix issues locally so the PR is clean. Also re-read the **Checklist Before Every PR** in
`docs/SECURITY.md`.

---

## 8. Where to read before coding

1. `CLAUDE.md` — project rules and non-negotiables
2. `codebase/STRUCTURE.md` — the file map + build order
3. `feature_plans/<your-feature>_plan.md` — the detailed spec for your task
4. `docs/EDGE_CASES.md` — failure modes + the pre-demo smoke test

---

## 9. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `docker: command not found` | Docker Desktop isn't installed/running. Start Docker Desktop and wait for it to say "running". |
| Docker error about WSL (Windows) | Run `wsl --install` in an Admin PowerShell, reboot. |
| `port already in use` (5000/5173/5432) | Something else is using it. Stop it, or change the port. Find it: `netstat -ano | findstr :5432` (Windows). |
| `Activate.ps1 cannot be loaded` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, reopen terminal. |
| `flask: command not found` | Your venv isn't activated, or deps not installed. Re-activate and `pip install -r requirements.txt`. |
| Backend can't reach the DB | Are the infra containers up? `docker compose -f infra/docker-compose.yml ps`. Check `DATABASE_URL` host is `postgres` (Docker) or `localhost` (local). |
| Browser: "connection not private" | Expected — self-signed cert. Click Advanced → Proceed. |
| `.env` changes not taking effect | Restart the backend / `docker compose ... up` again. Env is read at startup. |
| Merge conflict scares you | See 6.8, or ask. Nothing is broken until you commit. |
| Accidentally committed `.env` | Tell the team NOW, rotate the secrets, and remove it: `git rm --cached codebase/.env` then commit. |

---

## 10. Quick command reference

```bash
# Run full stack (Docker)
docker compose -f infra/docker-compose.yml up --build

# Run only infra (for local dev)
docker compose -f infra/docker-compose.yml up postgres redis minio vault

# Backend (from codebase/backend, venv active)
flask db upgrade         # apply migrations
flask db migrate -m "msg"# create a migration after model changes
python seed.py           # demo data
flask run --debug        # dev server

# Frontend (from codebase/frontend)
npm install
npm run dev

# Git daily flow
git checkout main && git pull
git checkout -b feature/my-task
git add <files> && git commit -m "feat: ..."
git push -u origin feature/my-task
gh pr create --base main --fill      # or open PR on GitHub
```

Welcome to the team. Ship securely. 🔐

---

## Appendix — creating the repo (ONE person does this once)

Only the person who first sets up GitHub needs this. Do it from the **project root** (the
`SIH26/` folder that contains `codebase/`, `docs/`, `feature_plans/`, `CLAUDE.md`) so all the
design docs are versioned too — not just `codebase/`.

```bash
cd path/to/SIH26           # the folder with CLAUDE.md + docs/ + codebase/
git init
git add .
git status                 # CONFIRM: no .env, no node_modules, no .venv is listed
git commit -m "chore: initial project scaffold and docs"

# Create the repo on GitHub (private!) and push. With gh CLI:
gh repo create leet-secure-dms --private --source=. --remote=origin --push
# ...or create it on github.com, then:
#   git remote add origin https://github.com/<org-or-user>/<repo>.git
#   git branch -M main
#   git push -u origin main
```

Then, in **GitHub → Settings → Branches → Add branch ruleset** for `main`:
- ✅ Require a pull request before merging
- ✅ Require at least **1 approval**
- ✅ Require branches to be up to date before merging
- ✅ Block force pushes

Finally, add all 5 teammates: **Settings → Collaborators → Add people**, and share the repo URL.
Everyone else starts at **section 2** of this guide.


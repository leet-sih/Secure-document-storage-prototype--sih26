# SETUP — Secure DMS (Team leet)

Onboarding guide for every teammate. Follow it top to bottom. Budget ~45 minutes the first time.

If you get stuck, search the **Troubleshooting** section at the bottom before pinging the group.

---

## 0. What you are setting up

A web app with three parts:

- **backend/** — Flask API (Python 3.12; 3.13/3.14 also work)
- **frontend/** — React 18 + Vite (TypeScript)
- **infra/** — PostgreSQL only (Docker). *Redis / MinIO / Vault / Nginx are deferred to
  production — not part of the prototype; see `codebase/infra/README.md`.*

**How it runs:** PostgreSQL in a Docker container; the backend and frontend run **directly on
your machine** with hot-reload. You need: Git + Docker Desktop + Python 3.12 + Node 20.

> **Scope note:** only the **auth** slice is runnable today — the migration creates `users`,
> `departments`, `audit_events`. Case/document/search features aren't migrated yet.

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

### 1.2 Extra tools for running the app (backend + frontend run locally)

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

Open `.env` and replace every `CHANGE_ME_generate_a_random_string`. For local dev you can keep
the simple DB values (e.g. `devpassword`), but the **three secrets must be real, distinct random
strings**: `SECRET_KEY`, `JWT_SECRET`, `KMS_WRAPPING_KEY` (they must all differ).

```bash
# Run three times; paste one each into SECRET_KEY, JWT_SECRET, KMS_WRAPPING_KEY
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

> 🔴 **NEVER commit `.env` or paste real secrets in Slack/WhatsApp/GitHub.** If you ever do
> by accident, tell the team immediately and rotate the value.

`KMS_WRAPPING_KEY` wraps document master keys and is a **separate secret** from `SECRET_KEY`
and `JWT_SECRET` — see `docs/SECURITY.md` "Key lifecycle".

---

## 4. Start PostgreSQL (Docker)

Only PostgreSQL runs in Docker. From the `codebase/` folder, create a container whose
credentials match `.env`:

```bash
docker run -d --name pramaan-postgres \
  -e POSTGRES_USER=dms_app_user -e POSTGRES_PASSWORD=devpassword -e POSTGRES_DB=dms \
  -p 5432:5432 postgres:16
```

PowerShell uses backtick (`` ` ``) line-continuations instead of `\`. Wait until it's ready:

```bash
docker exec pramaan-postgres pg_isready -U dms_app_user -d dms   # -> "accepting connections"
```

> **If port 5432 is already in use** (`Bind for 0.0.0.0:5432 failed: port is already allocated`),
> another Postgres is running. Don't kill it — map to **5433** instead
> (`-p 5433:5432`) and change `DATABASE_URL` in `.env` to `...@localhost:5433/dms`.
>
> Alternative: `docker compose --env-file .env -f infra/docker-compose.yml up -d postgres`.

## 5. Run the backend + frontend (locally, hot reload)

Open **two terminals**.

### 5.1 Backend

```bash
cd codebase/backend
python -m venv .venv

# Activate the virtual environment:
#   Windows PowerShell:  .venv\Scripts\Activate.ps1
#   macOS/Linux:         source .venv/bin/activate

pip install -r requirements.txt

flask --app wsgi:app db upgrade    # creates users, departments, audit_events
python seed.py                     # seeds ONE SUPER_ADMIN (prints the login)
flask --app wsgi:app run --port 5000
```

`seed.py` prints the only account — `admin@ncrb.gov.in / ChangeMe!2345` (SUPER_ADMIN). Every
other user is created by that admin in-app. Sanity check: `curl http://localhost:5000/health`.

> If `.venv\Scripts\Activate.ps1` is blocked on Windows, run once:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then reopen the terminal. You can also
> skip activation and call `.\.venv\Scripts\python.exe` / `...\flask.exe` directly.

### 5.2 Frontend

```bash
cd codebase/frontend
npm install
npm run dev        # http://localhost:5173  (proxies /api to the backend automatically)
```

Open **http://localhost:5173**. Backend changes reload on save; frontend hot-reloads instantly.

### 5.3 Walk through the auth flow

Log in as `admin@ncrb.gov.in` / `ChangeMe!2345`:

1. **Forced password change** (first login) — 12+ chars, upper + lower + digit + special.
2. **Forced MFA setup** — scan the QR with an authenticator app (or type the manual key),
   enter the 6-digit code → **Activate**. No phone?
   `python -c "import pyotp; print(pyotp.TOTP('MANUAL_KEY').now())"`.
3. **User Admin → Create User** — provision other users; each gets a one-time temp password
   and runs the same change-password + MFA setup on first login.

**Reset to a clean single-admin state anytime:**

```bash
docker exec pramaan-postgres psql -U dms_app_user -d dms \
  -c "TRUNCATE TABLE audit_events, users, departments RESTART IDENTITY CASCADE;"
python seed.py    # from codebase/backend, venv active
```

### 5.4 Daily "start work" checklist

```
1. git checkout main && git pull            # get latest
2. docker start pramaan-postgres            # (or the `docker run` in §4 the first time)
3. (backend terminal) activate venv -> flask --app wsgi:app run --port 5000
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
| `docker info` fails / daemon error | Start **Docker Desktop**, wait for "Engine running", retry. |
| Docker error about WSL (Windows) | Run `wsl --install` in an Admin PowerShell, reboot. |
| `port is already allocated` (5432) | Another Postgres is running. Use `-p 5433:5432` and set `DATABASE_URL` to `...@localhost:5433/dms` (see §4). |
| Backend won't start, `KeyError: 'SECRET_KEY'` | `.env` missing or still has `CHANGE_ME`. Redo §3. |
| `pip install` fails building a package | Prefer Python 3.12; recreate `.venv` with a 3.12 interpreter. |
| `Activate.ps1 cannot be loaded` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, reopen terminal. |
| `flask: command not found` | venv not activated / deps missing. Re-activate and `pip install -r requirements.txt`. |
| Backend can't reach the DB | Is the container up? `docker ps`. Check `DATABASE_URL` host/port matches the container (`localhost:5432` or `:5433`). |
| Login 401 for a known-good user | That account's password was changed in-app. Reset the DB (§5.3) to restore `ChangeMe!2345`. |
| `column "mfa_enabled" does not exist` in psql | It's a computed property, not a column. Query `totp_secret IS NULL` instead. |
| `.env` changes not taking effect | Restart the backend. Env is read at startup. |
| Merge conflict scares you | See 6.8, or ask. Nothing is broken until you commit. |
| Accidentally committed `.env` | Tell the team NOW, rotate the secrets, and remove it: `git rm --cached codebase/.env` then commit. |

---

## 10. Quick command reference

```bash
# Database (Postgres only) — first time
docker run -d --name pramaan-postgres \
  -e POSTGRES_USER=dms_app_user -e POSTGRES_PASSWORD=devpassword -e POSTGRES_DB=dms \
  -p 5432:5432 postgres:16
docker start pramaan-postgres          # subsequent runs

# Backend (from codebase/backend, venv active)
flask --app wsgi:app db upgrade          # apply migrations
flask --app wsgi:app db migrate -m "msg" # create a migration after model changes
python seed.py                           # seed the SUPER_ADMIN
flask --app wsgi:app run --port 5000     # dev server

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


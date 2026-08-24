# migrations/

Flask-Migrate (Alembic) migration scripts live here.

## First-time setup (Phase 0, run once)
```bash
flask db init          # creates the migrations/ scaffolding (env.py, versions/)
flask db migrate -m "phase 1: departments, users"
flask db upgrade
```

## Everyday flow
```bash
flask db migrate -m "add document_signatures"   # autogenerate from model changes
flask db upgrade                                 # apply
```

## Must be hand-written into migrations (autogenerate WON'T catch these)
- `audit_events`: `REVOKE UPDATE, DELETE ON audit_events FROM <app_db_user>;` (append-only)
- `documents`: `search_vector` trigger + GIN index (see search_plan.md)
- CHECK constraints for role / status / doc_type enums
- Composite/GIN indexes listed in the feature plans

The container entrypoint runs `flask db upgrade` on boot (idempotent) — see docs/EDGE_CASES.md 6.2.

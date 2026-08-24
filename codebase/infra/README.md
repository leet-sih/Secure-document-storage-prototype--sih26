# infra/ — infrastructure

## Prototype (now)
Only **PostgreSQL** runs as a container. Everything else runs on your machine or on local disk:

| Concern | Prototype | Where |
|---------|-----------|-------|
| Database | PostgreSQL (Docker) | `docker-compose.yml` |
| Backend | Flask dev server (local) | `../backend`, run with `flask run` |
| Frontend | Vite dev server (local) | `../frontend`, run with `npm run dev` |
| Encrypted chunks | local filesystem | `../backend/data/chunks/` |
| Master keys | local file KMS | `../backend/data/keys/` |

Start it:
```bash
docker compose -f infra/docker-compose.yml up postgres
```

## Future / production (when we scale up)
These come back later — the code already isolates them behind small interfaces so swapping them
in is low-effort:

- **MinIO / S3** — replaces the local chunk store (`storage/chunk_store.py`).
- **HashiCorp Vault** — replaces the local file KMS (`core/kms.py`).
- **Redis** — refresh-token store, rate-limit counters, TOTP replay guard.
- **Celery + beat** — scheduled cleanup, OCR, embeddings (`tasks/`).
- **Nginx + TLS** — reverse proxy, HTTPS, security headers.
- **Gunicorn** — production WSGI server.

See `docs/ARCHITECTURE.md` for the target architecture and `docs/SECURITY.md` for the hardening
that returns with them.

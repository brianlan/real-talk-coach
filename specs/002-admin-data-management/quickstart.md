# Admin Data Management Quickstart

## Prerequisites
- Backend and frontend apps installed per `README.md`
- Pre-shared admin token configured

## Environment

Add the following to `backend/.env`:

```
ADMIN_ACCESS_TOKEN=replace-with-strong-token
```

Add the following to `frontend/.env.local`:

```
NEXT_PUBLIC_ADMIN_TOKEN=replace-with-strong-token
```

## Run (dev)

Terminal 1 – backend API:
```
cd backend
uvicorn app.main:app --reload --env-file .env
```

Terminal 2 – frontend:
```
cd frontend
pnpm dev --port 3000
```

## Admin Pages

- Visit `http://localhost:3000/admin` to access admin management pages.
- If access is denied, verify the admin token matches backend configuration.

## Testing

Backend:
```
cd backend
ruff check .
pytest
```

Frontend:
```
cd frontend
pnpm lint
pnpm test
pnpm playwright test
```

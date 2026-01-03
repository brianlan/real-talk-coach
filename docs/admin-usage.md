# Admin Usage Notes

1. Set matching tokens in `backend/.env` (`ADMIN_ACCESS_TOKEN`) and `frontend/.env.local` (`NEXT_PUBLIC_ADMIN_TOKEN`).
2. Run backend (`uvicorn app.main:app --reload --env-file .env`) and frontend (`pnpm dev`).
3. Visit `http://localhost:3000/admin`.
4. Navigate via the Admin shell to manage Skills, Scenarios, Sessions, and Audit Log.
5. When editing entities, watch for optimistic concurrency messages (stale edits display inline errors).
6. Deleting records requires confirmation and may be blocked if the record is referenced elsewhere.
7. Measurement practices and SC-001..SC-004 runbooks live in `docs/admin-metrics.md`.

# Folder Structure Blueprint

This is the production folder layout to be used in the next phases. It keeps the browser client, API layer, database assets, and deployment assets separated.

```text
mmattend/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── recognition/
│   │   └── main.py
│   ├── tests/
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── store/
│   │   └── styles/
│   ├── package.json
│   └── vite.config.ts
├── database/
│   ├── migrations/
│   ├── seeds/
│   └── schema.sql
├── docs/
│   ├── phase-1-system-design.md
│   ├── api-spec.md
│   └── security-model.md
├── tests/
│   ├── e2e/
│   ├── performance/
│   └── fixtures/
├── mark_attendance.py
├── register_student.py
├── pahses
└── prompt
```

## Responsibility Split

- `backend/`: FastAPI application, business logic, recognition service integration, and reporting APIs.
- `frontend/`: React application, camera UI, MediaPipe worker integration, dashboards, and report screens.
- `database/`: SQL schema, migrations, seed data, and future policy scripts.
- `docs/`: architecture, API contracts, and security references.
- `tests/`: end-to-end, performance, and shared fixture assets.

## Notes

1. The current prototype scripts stay untouched for now; production implementation will move into `backend/` and `frontend/` in later phases.
2. Empty root directories were created in Phase 1 so Phase 2 can start directly with implementation.
3. Deployment target is source-based: Vercel for the frontend and Railway for the backend.
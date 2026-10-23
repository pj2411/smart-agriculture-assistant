# Smart Agriculture Assistant (JalSaathi)

Farmer-first climate monitoring, crop/disease prediction, and voice assistant app.

![Screenshot 1](docs/screenshots/screenshot-1.png)
![Screenshot 2](docs/screenshots/screenshot-2.png)


## Stack
- Frontend: React + Vite (`frontend/`)
- Backend: FastAPI (`backend/`)
- ML: crop & disease models (`ml/`)

## Run locally
Backend:
```bash
cd backend
../.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
```
Frontend:
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173

## Env
Copy `.env.example` to `.env` and fill values. For local dev, set `VITE_LOCAL_DEMO_AUTH=true`.

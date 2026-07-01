# Run Guide

To run Veloce Engine end-to-end, you need to start both the backend and frontend servers.

## 1. Start the Backend (FastAPI)

Open a terminal in the root directory:
```bash
cd backend
fastapi dev main.py
```
*(Alternatively, you can run `uvicorn backend.main:app --reload`)*

The backend will be available at:
- **API**: http://127.0.0.1:8000
- **Swagger Docs**: http://127.0.0.1:8000/docs

## 2. Start the Frontend (Vite/React)

Open a new terminal window in the root directory:
```bash
cd frontend
npm run dev
```

The frontend will be available at:
- **Application**: http://localhost:5173

# Bernie-SPSS

**Open-source, web-based statistical software for Vietnamese economics students.**

> Free alternative to SPSS — runs in any browser, no installation required.
> Built with FastAPI + Next.js 14 + shadcn/ui

---

## Features (MVP — Priority 1)

| # | Feature | Status |
|---|---------|--------|
| 1 | CSV / Excel Import | ✅ |
| 2 | SPSS .sav Import/Export | ✅ |
| 3 | Variable View Editor | ✅ |
| 4 | Frequencies | ✅ |
| 5 | Descriptive Statistics | ✅ |
| 6 | Crosstabs + Chi-Square | ✅ |
| 7 | Independent Samples T-Test | ✅ |
| 8 | Paired Samples T-Test | ✅ |
| 9 | One-Sample T-Test | ✅ |
| 10 | One-Way ANOVA + Post-hoc | ✅ |
| 11 | Pearson / Spearman Correlation | ✅ |
| 12 | OLS Linear Regression | ✅ |
| 13 | Binary Logistic Regression | ✅ |
| 14 | EFA (Factor Analysis) | ✅ |
| 15 | Reliability Analysis (Cronbach's α) | ✅ |
| 16 | Recode Variables | ✅ |
| 17 | Compute Variable | ✅ |
| 18 | Select Cases / Filter | ✅ |
| 19 | Sort Cases | ✅ |
| 20 | Export: Excel + PDF | ✅ |

---

## Quick Start (Docker)

```bash
# 1. Clone and copy env files
git clone https://github.com/yourorg/bernie-spss
cd bernie-spss
cp .env.example .env
cp frontend/.env.local.example frontend/.env.local

# 2. Start all services
docker-compose up --build

# 3. Open browser
open http://localhost:3000

# 4. Verify backend health
curl http://localhost:8000/health
# → {"status":"ok","sessions":0,"environment":"development"}
```

---

## Environment Setup (Local Development)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Start FastAPI
uvicorn app.main:app --reload --port 8000

# Start Celery worker (separate terminal)
celery -A app.tasks.celery_tasks worker --loglevel=info
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
# Open http://localhost:3000
```

### Redis (for Celery)

```bash
# Docker
docker run -d -p 6379:6379 redis:7-alpine

# macOS
brew install redis && redis-server
```

---

## Environment Variables

### Backend (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Celery broker + backend |
| `MAX_UPLOAD_MB` | `50` | Max file upload size |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS origins (comma-separated) |
| `ENVIRONMENT` | `development` | `development` or `production` |

### Frontend (`.env.local`)

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API base URL |

---

## Running Tests

```bash
cd backend
pytest tests/ -v

# Run specific test file
pytest tests/unit/test_descriptives.py -v
pytest tests/integration/test_api.py -v
```

---

## Deployment

### Render (Backend)

1. Create a **Web Service** pointing to `./backend`
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables from `.env`
5. Add a **Background Worker** for Celery: `celery -A app.tasks.celery_tasks worker --loglevel=info`
6. Use **Redis Cloud** (free 30MB tier) for `REDIS_URL`
7. Set up **cron-job.org** to ping `https://your-app.onrender.com/health` every 3 minutes (keeps free tier warm)

### Vercel (Frontend)

1. Import `./frontend` repository
2. Set `NEXT_PUBLIC_API_URL` to your Render backend URL
3. Deploy

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI + uvicorn + pydantic v2 |
| **Statistics** | scipy + statsmodels + pingouin + factor_analyzer |
| **File I/O** | pyreadstat (SPSS .sav), pandas (CSV/Excel) |
| **Task Queue** | Celery + Redis |
| **Export** | openpyxl (Excel), WeasyPrint (PDF) |
| **Frontend** | Next.js 14 + TypeScript + Tailwind CSS |
| **UI Components** | shadcn/ui + Radix UI |
| **Tables** | TanStack Table v8 + TanStack Virtual v3 |
| **State** | Zustand |
| **Charts** | Plotly.js |
| **HTTP Client** | Axios + TanStack Query |

---

## Architecture

```
bernie-spss/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── core/                # Config, exceptions
│   │   ├── domain/
│   │   │   ├── models/          # Pydantic domain models
│   │   │   └── services/        # Pure statistical functions
│   │   ├── api/
│   │   │   ├── routes/          # HTTP route handlers
│   │   │   └── schemas/         # Request/Response schemas
│   │   └── tasks/               # Celery async tasks
│   └── tests/
├── frontend/
│   └── src/
│       ├── app/                 # Next.js App Router pages
│       ├── components/          # UI components
│       ├── stores/              # Zustand state
│       ├── lib/                 # API client, utilities
│       └── types/               # TypeScript interfaces
└── docker-compose.yml
```

---

## License

MIT License — Free for academic and commercial use.

Built for Vietnamese economics students 🇻🇳

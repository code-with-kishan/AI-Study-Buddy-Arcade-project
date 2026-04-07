# AI Study Buddy (Production-Ready Flask Platform)

AI Study Buddy is a full multi-page learning platform built with Flask + SQLite, featuring AI-assisted study workflows, gamified progress, tests, contests, reminders, printable reports/certificates, 3D concept previews, and deployment-ready infrastructure.

## Live Links

- GitHub: https://github.com/code-with-kishan/AI-Study-Buddy-Arcade-project.git
- Deployment (Render): https://ai-study-buddy-arcade-project-dp.onrender.com

## Complete Feature List

### 1) Public Experience

- Premium landing page for logged-out users.
- Animated UI interactions on landing (card hover effects, button hover effects, cursor sparkles).
- Built-in floating landing helper chatbot.
- Login and signup CTA in landing navbar.

### 2) Authentication and Access Control

- Signup with avatar selection.
- Login and logout flow.
- Session-based authentication with protected routes.
- User-specific private data separation.

### 3) Post-Login UI/UX System

- Shared authenticated layout with sidebar + main content.
- Premium top navbar on all authenticated pages.
- Active-link highlighting in navbar.
- Sidebar toggle support and mobile off-canvas drawer.
- Strict mobile optimization to avoid overlap.
- Dark/light theme toggle.
- Floating in-app study buddy assistant panel.

### 4) Core Learning Modules

- AI Chat (`/chat`) with modes:
  - Explain
  - Summarize
  - Quiz
  - Flashcards
- Difficulty control.
- AI provider control (Gemini/OpenRouter with fallback behavior).
- PDF upload + extraction for AI-assisted analysis.

### 5) Notes and Study Content

- Notes Lab (`/notes-lab`) with 3 sources:
  - Last chat response
  - Uploaded PDF
  - Manual summary input
- Teacher strictness modes (normal/strict/very_strict).
- Handwritten-style notes PDF export.
- Notes export history persisted in database.

### 6) Topic Learning and Practice

- Topic Learning (`/topic-learning`) with explanation generation.
- Structured notes points and practice questions generation.
- Graphs module (`/graphs`) with equation plotting and custom coordinate plotting.
- PYQ module (`/pyq`) with exam-wise question banks and attempt tracking.
- Demo Test (`/demo-test`) with score + weak topic analysis.
- Mock Test (`/mock-test`) with score + weak topic analysis + suggestions.

### 7) Gamification and Progress

- XP engine with event-based XP updates.
- XP Center (`/xp-center`) with levels and ranking table.
- Dashboard (`/dashboard`) with stats and quiz history.
- Leaderboard APIs and leaderboard views merged into XP flow.

### 8) Streaks, Contest, Reminders

- Streak page (`/streak`) with streak calendar.
- One-hour study logging API (`/api/streak/log-hour`).
- Weekly Contest (`/weekly-contest`) with weekly leaderboard persistence.
- Reminders module (`/reminders`) with reminder type and date-time scheduling.

### 9) Reporting and Certificates

- Report Card page (`/report-card`).
- Report Card PDF download (`/report-card.pdf`).
- Mock certificate PDF download (`/certificate.pdf`).
- Landscape-formatted report/certificate design.

### 10) 3D Learning

- 3D Models page (`/models-3d`).
- GLB model preview support with fallback rendering.
- Demo model mapping and model info display.
- 3D performance optimizations for faster rendering.

### 11) Profile and Personalization

- Profile update (username/avatar/password handling).
- Owner chatbot memory customization.
- Personalization fields (role, bio, learning goals).

### 12) Reliability, Security, Operations

- Password hashing via Werkzeug.
- Input validation and controlled parameter sets.
- Retry/backoff around AI provider calls.
- Safe markdown rendering with bleach sanitization.
- API/cache/security headers.
- Health endpoint (`/healthz`) with DB and provider configuration status.

## Tech Stack

- Backend: Python, Flask
- Database: SQLite
- AI Providers: Google Gemini, OpenRouter
- Frontend: Jinja2 templates, HTML, CSS, JavaScript
- PDF/Doc Tooling: pypdf, reportlab, markdown, bleach
- Reliability: tenacity
- Production: Gunicorn, Nginx, Docker Compose
- Testing: Python unittest

## Project Structure

```text
AI-Study-Buddy/
├── app.py
├── requirements.txt
├── .env.example
├── Makefile
├── Dockerfile
├── docker-compose.prod.yml
├── gunicorn.conf.py
├── nginx.conf
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── signup.html
│   ├── chat.html
│   ├── dashboard.html
│   ├── notes_lab.html
│   ├── topic_learning.html
│   ├── graphs.html
│   ├── pyq.html
│   ├── demo_test.html
│   ├── mock_test.html
│   ├── streak.html
│   ├── weekly_contest.html
│   ├── reminders.html
│   ├── report_card.html
│   ├── models_3d.html
│   ├── profile.html
│   └── xp_center.html
├── static/
│   └── models/
├── tests/
│   └── test_app.py
└── README.md
```

## Environment Setup

1. Clone repository

```bash
git clone https://github.com/code-with-kishan/AI-Study-Buddy-Arcade-project.git
cd AI-Study-Buddy-Arcade-project
```

2. Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Create env file

```bash
cp .env.example .env
```

5. Configure environment variables

```dotenv
GEMINI_API_KEY=your_gemini_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
FLASK_SECRET_KEY=replace_with_a_long_random_secret
FLASK_DEBUG=false
LOG_LEVEL=INFO
REQUEST_TIMEOUT=25
RATE_LIMIT_PER_MINUTE=45
DATABASE_FILE=database.db
OPENROUTER_MODEL=openai/gpt-3.5-turbo
WEB_CONCURRENCY=2
GUNICORN_THREADS=2
GUNICORN_TIMEOUT=60
GUNICORN_GRACEFUL_TIMEOUT=30
GUNICORN_KEEPALIVE=5
GUNICORN_BIND=0.0.0.0:8000
```

## Development Commands

From project root:

```bash
make install      # Install dependencies
make dev          # Run Flask app
make test         # Run tests
make lint         # Compile/syntax checks
make health       # Health check on /healthz
make prod-up      # Start Docker production stack
make prod-down    # Stop Docker production stack
```

Notes:

- Default dev command runs on port 5000.
- If macOS system services occupy 5000, run app manually on another port (for example 5050).

## Routes and APIs

### Page Routes

- GET `/`
- GET|POST `/signup`
- GET|POST `/login`
- GET `/logout`
- GET|POST `/profile`
- GET|POST `/chat`
- GET `/dashboard`
- GET `/xp-center`
- GET|POST `/notes-lab`
- GET|POST `/topic-learning`
- GET `/graphs`
- GET|POST `/pyq`
- GET|POST `/demo-test`
- GET|POST `/mock-test`
- GET `/certificate.pdf`
- GET `/streak`
- GET|POST `/weekly-contest`
- GET|POST `/reminders`
- GET `/report-card`
- GET `/report-card.pdf`
- GET `/models-3d`

### API Routes

- POST `/save_score`
- POST `/api/assistant`
- GET `/api/history`
- GET `/api/stats`
- GET `/api/leaderboard`
- POST `/api/streak/log-hour`
- GET `/healthz`

## Deployment

### Vercel Frontend + Render Backend (Recommended for your setup)

This repository is now compatible with Vercel + Render deployment in two modes.

Mode A (fastest): Vercel reverse-proxies all routes to Render backend.

1. Deploy backend to Render using `render.yaml`.
2. Set backend env vars in Render:
  - `GEMINI_API_KEY`
  - `OPENROUTER_API_KEY`
  - `FLASK_SECRET_KEY`
  - `FRONTEND_ORIGIN=https://your-vercel-domain.vercel.app`
  - `CORS_ALLOWED_ORIGINS=https://your-vercel-domain.vercel.app`
3. In `vercel.json`, replace:
  - `https://YOUR-RENDER-BACKEND.onrender.com`
  with your real Render service URL.
4. Deploy this repo on Vercel.

Result: your Vercel domain serves the app, while backend runtime stays on Render.

Mode B (true split): host a separate frontend project on Vercel and call this backend as API.

For Mode B, keep the same backend CORS env vars (`FRONTEND_ORIGIN` and `CORS_ALLOWED_ORIGINS`) and send credentials on frontend requests when using session auth.

### Render

- Live URL: https://ai-study-buddy-arcade-project-dp.onrender.com
- Configure the same env vars as `.env.example`.
- `render.yaml` is included for one-click Blueprint setup.

### Docker Compose (Nginx + Gunicorn)

```bash
make prod-up
```

Open:

- App: http://localhost
- Health: http://localhost/healthz

Stop:

```bash
make prod-down
```

### Gunicorn only

```bash
gunicorn -c gunicorn.conf.py app:app
```

## Testing

```bash
make test
```

Current tests cover auth flow, protected routes, profile updates, score/stat/history/leaderboard behavior, and assistant API behavior.

## Owner

- Kishan Nishad
- LinkedIn: https://www.linkedin.com/in/kishan-nishad-161a73392

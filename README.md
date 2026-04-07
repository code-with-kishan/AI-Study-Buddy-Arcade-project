<div align="center">

![AI Study Buddy Banner](https://capsule-render.vercel.app/api?type=waving&height=220&color=0:0f172a,50:1d4ed8,100:0ea5e9&text=AI%20Study%20Buddy&fontColor=ffffff&fontSize=54&fontAlignY=40&desc=Your%20Private%20Premium%20Learning%20OS&descAlignY=62)

[![Typing SVG](https://readme-typing-svg.demolab.com?font=Space+Grotesk&weight=700&size=24&duration=2600&pause=900&color=FACC15&center=true&vCenter=true&width=980&lines=AI+Chat+%2B+Notes+Lab+%2B+PYQ+%2B+3D+Models+%2B+Contests;Gamified+XP+Engine+with+Reports%2C+Certificates%2C+Streaks;Flask+Production+Build+Deployed+on+Render+%2B+Vercel)](https://git.io/typing-svg)

[![Vercel](https://img.shields.io/badge/Live%20Frontend-Vercel-000000?style=for-the-badge&logo=vercel)](https://aistudybuddy-pi.vercel.app)
[![Render](https://img.shields.io/badge/Live%20Backend-Render-46E3B7?style=for-the-badge&logo=render&logoColor=000)](https://aistudybuddy-pdrp.onrender.com/healthz)
[![Flask](https://img.shields.io/badge/Backend-Flask-111827?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-0B1220?style=for-the-badge&logo=sqlite)](https://www.sqlite.org/)
[![Gemini](https://img.shields.io/badge/AI-Gemini%20%2B%20OpenRouter-1d4ed8?style=for-the-badge)](#)

</div>

## What Is AI Study Buddy?

AI Study Buddy is a full-featured, multi-page study platform that combines AI learning workflows, gamification, test analytics, reminders, and visual learning tools in a premium UI.

This project is not a simple chat app. It is a complete personal study ecosystem with:

- smart AI study modes
- notes and PDF pipelines
- report cards and certificates
- streak and contest systems
- 3D model learning
- profile personalization
- mobile-first responsive UX

## Live Links

- Frontend (Vercel): https://aistudybuddy-pi.vercel.app
- Backend Health (Render): https://aistudybuddy-pdrp.onrender.com/healthz
- GitHub: https://github.com/code-with-kishan/AI-Study-Buddy-Arcade-project.git

---

## Feature Universe (Minor to Major)

### Public Experience

- Premium landing page for logged-out users.
- Animated landing interactions:
  - flip/tilt card hover
  - CTA hover animation
  - cursor sparkle trail
  - chatbot floating assistant
- Login/signup navigation in landing header.

### Authentication and Access

- Signup with avatar picker.
- Login/logout flow.
- Session-based protected routing.
- Per-user private data isolation.

### Premium Post-Login UI System

- Shared authenticated shell.
- Premium top navbar on after-login pages.
- Active route highlight in top nav.A
- Sidebar with desktop persistent mode.
- Sidebar off-canvas drawer on mobile.
- Sidebar toggle button and backdrop close.
- No-overlap responsive behavior.
- Dark/light theme toggle.

### AI Learning Core

- AI Chat at `/chat` with 4 modes:
  - explain
  - summarize
  - quiz
  - flashcards
- Difficulty controls.
- Provider controls (Gemini/OpenRouter).
- Provider fallback strategy.
- PDF text extraction and AI summarization from uploaded PDFs.

### Notes and Content Intelligence

- Notes Lab (`/notes-lab`) supports:
  - notes from last chat output
  - notes from PDF upload
  - notes from manual summary input
- Teacher style modes:
  - normal
  - strict
  - very_strict
- Clean handwritten-style notes generation.
- Notes PDF export pipeline.
- Notes export history in DB.

### Topic Learning Engine

- Topic learning page with AI explanation generation.
- Auto-generated concise point-wise notes.
- Practice question generation for each topic.
- Exam-oriented guidance tone based on strictness mode.

### Visual Learning and Problem Solving

- Graph module (`/graphs`) with equation plotting.
- Custom coordinate point plotting.
- PYQ module (`/pyq`) with exam-wise question bank.
- Attempt cap + attempt tracking for PYQs.
- Auto solution reveal based on attempt logic.

### Test and Analysis Suite

- Demo Test module (`/demo-test`).
- Mock Test module (`/mock-test`).
- Score analytics with weak-topic extraction.
- Mock test suggestions for improvement.
- Score persistence in DB.

### XP, Leveling, and Competition

- XP rules engine for multiple actions.
- XP event tracking.
- Dashboard stats and history.
- XP Center with level ladders and badges.
- Leaderboard API and leaderboard views merged into XP center.
- Weekly Contest module with weekly score board.

### Streak and Reminder Productivity

- Study streak calendar view (`/streak`).
- 1-hour log API (`/api/streak/log-hour`).
- Reminder management (`/reminders`) with type/date-time.

### Reporting and Credential Exports

- Report Card page (`/report-card`).
- Report Card PDF (`/report-card.pdf`).
- Mock Certificate PDF (`/certificate.pdf`).
- Landscape styled formal report/certificate templates.

### 3D Concept Lab

- 3D Models page (`/models-3d`).
- GLB model loading support.
- Fallback rendering when model fails.
- Demo model cards with identity/details.
- 3D rendering optimizations for smoother UX.

### Profile, Personalization, Assistant Memory

- Profile updates for username/avatar/password.
- User personalization fields:
  - role
  - bio
  - learning goal
- Owner profile memory for assistant responses.

### Security, Reliability, and Platform Ops

- Password hashing with Werkzeug.
- Request validation and allow-lists.
- Rate limiting for POST endpoints.
- Retries with exponential backoff for AI calls.
- Safe markdown rendering with bleach.
- Security headers and API cache controls.
- Health endpoint with real runtime diagnostics:
  - database status
  - provider key status
  - auth state
  - timestamp

---

## Route Map

### Pages

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

### APIs

- POST `/save_score`
- POST `/api/assistant`
- GET `/api/history`
- GET `/api/stats`
- GET `/api/leaderboard`
- POST `/api/streak/log-hour`
- GET `/healthz`

---

## Tech Stack

| Layer | Stack |
|---|---|
| Backend | Python, Flask |
| Database | SQLite |
| AI | Gemini, OpenRouter |
| Frontend | Jinja2, HTML, CSS, JavaScript |
| PDF/Docs | pypdf, reportlab, markdown, bleach |
| Reliability | tenacity |
| Runtime | Gunicorn, Nginx, Docker Compose |
| Testing | unittest |

---

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
├── render.yaml
├── vercel.json
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

---

## Quickstart

```bash
git clone https://github.com/code-with-kishan/AI-Study-Buddy-Arcade-project.git
cd AI-Study-Buddy-Arcade-project
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
make dev
```

### Required Environment Variables

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

# Vercel + Render compatibility
SESSION_COOKIE_SECURE=true
FRONTEND_ORIGIN=https://aistudybuddy-pi.vercel.app
CORS_ALLOWED_ORIGINS=https://aistudybuddy-pi.vercel.app
```

---

## Deployment (Vercel + Render)

### Production Topology

- Frontend domain on Vercel.
- Backend runtime on Render.
- Vercel rewrites forward traffic to Render backend.

### Steps

1. Deploy backend on Render using `render.yaml`.
2. Ensure backend env keys are configured.
3. Set Render CORS/session values:
   - `FRONTEND_ORIGIN=https://aistudybuddy-pi.vercel.app`
   - `CORS_ALLOWED_ORIGINS=https://aistudybuddy-pi.vercel.app`
4. Deploy repo on Vercel.
5. Confirm `vercel.json` destination points to:
   - `https://aistudybuddy-pdrp.onrender.com`
6. Validate:
   - app: https://aistudybuddy-pi.vercel.app
   - health: https://aistudybuddy-pdrp.onrender.com/healthz

---

## Dev Commands

```bash
make install
make dev
make test
make lint
make health
make prod-up
make prod-down
```

---

## Health Output Example

```json
{
  "authenticated": false,
  "database": "ok",
  "gemini_configured": true,
  "openrouter_configured": true,
  "status": "ok",
  "timestamp": "2026-04-07T08:28:36.226502Z"
}
```

This means backend, database, and AI keys are configured correctly.

---

## Maintainer

- Kishan Nishad
- LinkedIn: https://www.linkedin.com/in/kishan-nishad-161a73392

<div align="center">

### Built for focused learners who want results, not noise.

</div>

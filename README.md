# 🎮 AI Study Buddy (Production-Ready)

AI Study Buddy is a multi-page Flask learning platform with authentication, AI-assisted study tools, gamified XP progression, private analytics, leaderboard, PDF support, and deployment-ready infrastructure.

## 🔗 Live Links

- GitHub: https://github.com/code-with-kishan/AI-Study-Buddy-Arcade-project.git
- Deployment (Render): https://ai-study-buddy-arcade-project-dp.onrender.com

## ✨ Current Features

- Secure auth flow: `signup`, `login`, `logout`
- Private user data (scores, stats, XP, events)
- AI chat modes: Explain, Summarize, Quiz, Flashcards
- Provider fallback: Gemini ↔ OpenRouter
- PDF upload analysis (`pypdf` extraction)
- Quiz scoring with XP rewards
- XP center with level badges (Bronze → Legend)
- Leaderboard by XP ranking
- Exports:
  - `GET /export_scores.pdf`
  - `GET /export_response.pdf`
- Health pages:
  - `GET /health`
  - `GET /healthz`
- Floating assistant with local FAQ + owner-profile-aware answers
- Dark/Light theme toggle
- Responsive dashboard-style UI with sidebar/footer

## 🧱 Tech Stack

- Backend: Python, Flask, SQLite
- AI: Google Gemini, OpenRouter
- Frontend: Jinja2 templates, HTML/CSS/JS
- PDF/Docs: `pypdf`, `reportlab`, `markdown`, `bleach`
- Reliability: `tenacity` retries, rate limiting, security headers
- Production: Gunicorn, Nginx, Docker Compose, GitHub Actions CI

## 📂 Project Structure

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
│   ├── login.html
│   ├── signup.html
│   ├── chat.html
│   ├── dashboard.html
│   ├── profile.html
│   ├── leaderboard.html
│   ├── xp_center.html
│   └── health.html
├── tests/
│   └── test_app.py
└── README.md
```

## ⚙️ Environment Setup

1) Clone repository

```bash
git clone https://github.com/code-with-kishan/AI-Study-Buddy-Arcade-project.git
cd AI-Study-Buddy-Arcade-project
```

2) Create and activate virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

3) Install dependencies

```bash
pip install -r requirements.txt
```

4) Create environment file

```bash
cp .env.example .env
```

5) Add required keys in `.env`

```dotenv
GEMINI_API_KEY=your_gemini_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
FLASK_SECRET_KEY=replace_with_a_long_random_secret
FLASK_DEBUG=false
```

## 🧪 Development Commands (Makefile)

Use these commands from project root:

```bash
make install      # Install dependencies
make dev          # Run local Flask app
make test         # Run unit tests
make lint         # Python compile/syntax check
make health       # Check local /healthz
make prod-up      # Start Docker production stack
make prod-down    # Stop Docker production stack
```

### Notes for `make dev`

- App runs on `http://127.0.0.1:5000` by default.
- If port `5000` is busy on macOS (AirPlay/ControlCenter), free it or run with another port strategy.

## 🧭 Main Routes

### Pages

- `GET /` (redirect)
- `GET|POST /signup`
- `GET|POST /login`
- `GET /logout`
- `GET|POST /chat`
- `GET /dashboard`
- `GET|POST /profile`
- `GET /leaderboard`
- `GET /xp-center`
- `GET /health`

### APIs

- `POST /save_score`
- `POST /api/assistant`
- `GET /api/stats`
- `GET /api/history?limit=10&q=topic`
- `GET /api/leaderboard`
- `GET /healthz`

### Export Endpoints

- `GET /export_scores.pdf`
- `GET /export_response.pdf`

## 🔐 Security & Reliability

- Password hashing with Werkzeug
- Input validation + controlled mode/provider/difficulty values
- Request rate limiting for POST APIs
- Retry/backoff for external AI provider calls
- Safe markdown rendering with `bleach`
- Security headers (`X-Frame-Options`, `X-Content-Type-Options`, etc.)

## 🚀 Deployment

### A) Render (already live)

- Live URL: https://ai-study-buddy-arcade-project-dp.onrender.com
- Configure env vars in Render dashboard (same keys as `.env.example`).

### B) Docker Compose (Nginx + Gunicorn)

```bash
make prod-up
```

Open:

- App: `http://localhost`
- Health: `http://localhost/healthz`

Stop stack:

```bash
make prod-down
```

### C) Gunicorn (without Docker)

```bash
gunicorn -c gunicorn.conf.py app:app
```

## ✅ Testing

Run:

```bash
make test
```

Current test suite covers:

- Auth-protected routes
- Profile updates
- Score/stat/history/leaderboard flow
- PDF export endpoints
- Assistant API behavior

## 📦 CI/CD

- GitHub Actions workflow: `.github/workflows/ci.yml`
- Includes install + test pipeline for regression checks.

## 👤 Owner

- Kishan Nishad
- LinkedIn: https://www.linkedin.com/in/kishan-nishad-161a73392

---

If you like this project, please ⭐ the repository.

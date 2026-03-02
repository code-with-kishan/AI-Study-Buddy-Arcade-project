# 🎮 AI Study Buddy – Gamified AI Learning Platform

An intelligent, arcade-style AI-powered learning platform that combines 
explanations, quizzes, flashcards, gamification, and dual AI reliability 
into one unified system.

---

## 📌 Overview

AI Study Buddy is a next-generation EdTech platform designed to enhance student engagement through:

- 🧠 AI-powered topic explanation
- 📝 Smart note summarization
- ❓ Dynamic MCQ quiz generation
- 🃏 Flashcard creation
- 🎮 XP-based gamification system
- 🏆 Level-up progress tracking
- 🔁 AI engine auto-fallback system
- 🤖 Dual AI integration (Gemini + OpenRouter)
- 🎨 Arcade-style interactive UI

This platform solves real-world learning challenges by combining AI + Gamification + API Redundancy.

---

## 🚨 Problem Statement

Students face multiple learning challenges:

- Difficulty understanding complex topics  
- Lack of personalized explanation  
- No interactive revision tools  
- Limited practice MCQs  
- No gamified motivation system  
- Dependency on a single AI service  

Existing platforms do not combine:
- AI explanation  
- Quiz generation  
- Flashcards  
- Gamification  
- API redundancy  

---

## 💡 Proposed Solution

AI Study Buddy provides:

- Real-time AI explanations  
- Automatic quiz generation  
- Flashcard learning system  
- XP & level-based progression  
- Dual AI engine fallback mechanism  
- Reliable performance even during API downtime  

---

## 🛠️ Tech Stack

### 🔹 Backend
- Python
- Flask
- SQLite
- Google Gemini API
- OpenRouter API
- REST API handling

### 🔹 Frontend
- HTML5
- CSS3
- JavaScript
- Jinja2
- Gamified animations

### 🔹 AI Models
- Gemini Flash (Primary)
- OpenRouter GPT-3.5 (Backup)

---

## ⚙️ System Architecture Flow

1. User selects:
   - AI Engine
   - Mode (Explain / Quiz / Flashcards)
   - Difficulty level

2. Dynamic prompt generation

3. API Call:
   - If Gemini fails → Switch to OpenRouter
   - If both fail → Show fallback message

4. Quiz Parsing Algorithm:
   - Extract questions
   - Extract options
   - Store correct answers
   - Enforce single option selection

5. Score Calculation:
   - Compare answers
   - Highlight correct/wrong
   - Update XP bar
   - Trigger level-up animation

6. Save results in SQLite database

---

## 🚀 Features

✔ AI-based explanations  
✔ Dynamic MCQ generation  
✔ Flashcard creation  
✔ XP gamification system  
✔ AI auto-fallback system  
✔ SQLite result storage  
✔ Arcade-style interactive UI  
✔ Fast response time (~1–3 seconds)  

---

## 📂 Project Structure

AI-Study-Buddy/
│
├── app.py
├── database.db
├── requirements.txt
├── .env.example
├── static/
├── templates/index.html
└── README.md

---

## 🔧 Installation & Setup (copy and run this commands on terminal)

### 1️⃣ Clone Repository

git clone https://github.com/code-with-kishan/AI-Study-Buddy-Arcade-project.git
cd AI-Study-Buddy-Arcade-project


### 2️⃣ Create Virtual Environment

python3 -m venv venv
source venv/bin/activate


### 3️⃣ Install Dependencies

pip install -r requirements.txt


### 4️⃣ Setup Environment Variables 

cp .env.example .env

Add your API keys:

GEMINI_API_KEY=your_gemini_key_here
OPENROUTER_API_KEY=your_openrouter_key_here


### 5️⃣ Run Application

python app.py

click on: http://127.0.0.1:5000 (Open browser)


---

## 🌍 Deployment Options

- Local Flask Server
- Google Cloud Run
- Render
- Railway
- Streamlit (alternative)

---

## 📊 Results

The system successfully:

✔ Generates AI explanations  
✔ Generates dynamic quizzes  
✔ Prevents multi-option selection errors  
✔ Auto-switches AI during quota limits  
✔ Saves quiz results  
✔ Provides smooth arcade-style UI  

---

## 🔮 Future Scope

- User authentication system  
- Leaderboard & ranking  
- Persistent XP tracking  
- Advanced UI sound effects  
- AI explanation after wrong answers  
- Multi-language support  
- Full cloud deployment  
- Mobile application version  

---

## 📚 References

- Google Gemini API Documentation  
- OpenRouter API Documentation  
- Flask Documentation  
- Python Official Documentation  
- SQLite Documentation  

---

## 🔗 Project Links

GitHub Repository:  https://github.com/code-with-kishan/AI-Study-Buddy-Arcade-project.git

Deployment Link:  https://ai-study-buddy-arcade-project-dp.onrender.com

---

## 🏆 Conclusion

AI Study Buddy demonstrates:

- Real-time AI learning integration  
- Smart API fallback mechanism  
- Gamification for engagement  
- Scalable backend architecture  
- Industry-ready implementation  

This project bridges the gap between AI-powered education and interactive gaming-based motivation.

---

⭐ If you like this project, consider giving it a star!

---

## ✅ Production-Ready Upgrades Included

- Input validation for mode, provider, difficulty, score ranges
- API retry/backoff for AI providers (`tenacity`)
- Automatic Gemini quota fallback to OpenRouter
- Secure markdown sanitization (`bleach`)
- Basic per-IP rate limiting for POST requests
- Security headers (`X-Frame-Options`, `X-Content-Type-Options`, etc.)
- Health endpoint for uptime checks (`/healthz`)
- Analytics endpoints (`/api/stats`, `/api/history`)
- CSV export endpoint (`/export_scores.csv`)
- SQLite index optimization on score history date

---

## 🆕 Advanced Product Features Added

- Authentication system (`/signup`, `/login`, `/logout`)
- User-created password for future login
- Avatar picker at signup (game-style cartoon avatars)
- Private-by-user analytics and score history
- Separate app pages (`login`, `signup`, `chat`, `dashboard`, `leaderboard`, `health`)
- Sidebar + footer layout for dashboard navigation
- Search in personal quiz history by topic
- PDF upload + AI processing for summary/explanation
- XP system for each completed task and quiz submission
- Global leaderboard ranking by XP
- PDF export for score report (`/export_scores.pdf`)
- PDF export for latest AI answer (`/export_response.pdf`)
- Profile page for avatar and password updates (`/profile`)
- XP levels and badges (Bronze → Legend)

---

## 🧩 New API Endpoints

- `GET /healthz` → app/db/provider health status
- `GET /api/stats` → attempts, total score, total questions, average percentage
- `GET /api/history?limit=10` → latest quiz attempts
- `GET /export_scores.csv` → downloadable score history

---

## 🔐 Environment Variables

Configure these in `.env`:

- `GEMINI_API_KEY`
- `OPENROUTER_API_KEY`
- `FLASK_SECRET_KEY`
- `FLASK_DEBUG` (recommended: `false`)
- `LOG_LEVEL` (recommended: `INFO`)
- `REQUEST_TIMEOUT` (seconds)
- `RATE_LIMIT_PER_MINUTE`
- `DATABASE_FILE`
- `OPENROUTER_MODEL`

---

## 🚀 Run in Production

Use Gunicorn instead of Flask dev server:

```bash
gunicorn -w 2 -b 0.0.0.0:5000 app:app
```

---

## 🐳 Docker + Nginx Deployment

Production files added:

- `Dockerfile`
- `gunicorn.conf.py`
- `nginx.conf`
- `docker-compose.prod.yml`
- `.dockerignore`

Run with Docker Compose:

```bash
docker compose -f docker-compose.prod.yml up --build
```

Then open:

- `http://localhost`
- Health check: `http://localhost/healthz`

---

## ✅ CI Pipeline

GitHub Actions workflow added at:

- `.github/workflows/ci.yml`

CI runs:

- Dependency installation
- Python compile/syntax validation
- Automated unit tests (`tests/test_app.py`)

---

## ⚡ Makefile Commands

Quick commands added in `Makefile`:

- `make install` → install dependencies
- `make dev` → run local app
- `make test` → run automated tests
- `make lint` → compile/syntax check
- `make prod-up` → start Docker production stack
- `make prod-down` → stop Docker production stack

---

## 📋 Release Checklist

Production release checklist added at:

- `RELEASE_CHECKLIST.md`

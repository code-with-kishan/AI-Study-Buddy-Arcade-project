# AI Study Buddy Production Rebuild

## 1) Migration Strategy

- Keep legacy Flask app running as fallback.
- Introduce new modular stack under `apps/`.
- Move traffic to Next.js + FastAPI after parity checks.

## 2) Final Stack

- Frontend: Next.js App Router (`apps/frontend`)
- Backend: FastAPI (`apps/backend`)
- DB: PostgreSQL
- AI Layer: Provider abstraction (`app/services/ai_provider.py`)
- Infra: Docker Compose (`infra/docker-compose.yml`)

## 3) Product Modules Implemented

1. AI Doubt Solver: text/image/pdf + teacher modes + quick actions.
2. Notes Engine: chat/pdf to structured notes + handwritten-style flag.
3. PYQ Practice: question bank + 2 attempt rule + solution + audio link.
4. Weak Topic Detection: wrong attempts + time taken -> weakness score.
5. Mock Test System: timed test model + scoring + post-analysis.
6. Study Streak: day-wise activity and GitHub-style intensity API.
7. AI Teacher Modes: friendly/strict/motivator.
8. Topic Explorer: explanation + key points + formulas + diagram block.
9. Graph/Visual Support: graph payload endpoint for math/physics.
10. Basic 3D Visualization: only selected topics.
11. Reminder + Pomodoro: reminders and focus session APIs.
12. Weekly Contest: weekly quiz and leaderboard.

## 4) Monetization Hooks

- `User.plan_type`: free/premium.
- Daily free AI limit enforced in doubt solver.
- Premium bypasses query cap.

## 5) Clean Separation

- AI logic: `app/services/ai_provider.py`
- Business logic: routers + `app/services/learning.py`
- Data layer: `app/models/entities.py`
- UI layer: Next.js route screens under `apps/frontend/app`

## 6) Immediate Next Steps

- Replace AI stub with Gemini/OpenRouter adapters and retries.
- Add Alembic migrations and CI checks.
- Add Redis queue + scheduler for reminders.
- Add payment integration (Stripe) for premium plan activation.

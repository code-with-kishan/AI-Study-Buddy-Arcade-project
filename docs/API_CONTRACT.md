# API Contract (FastAPI)

Base: `/api/v1`

## Auth
- `POST /auth/signup`
- `POST /auth/login`
- `GET /auth/me`

## Dashboard
- `GET /dashboard`

## Doubt Solver
- `POST /doubt-solver/solve`
- `POST /doubt-solver/solve-image`
- `POST /doubt-solver/solve-pdf`

## Notes
- `POST /notes/from-chat`
- `POST /notes/from-pdf`
- `GET /notes`

## PYQ Practice
- `GET /pyq/questions?topic=&difficulty=`
- `POST /pyq/attempt`

## Analytics
- `GET /analytics/weak-topics`
- `GET /analytics/progress?days=30`

## Mock Tests
- `GET /mock-tests`
- `POST /mock-tests/start`
- `POST /mock-tests/{attempt_id}/submit`

## Streaks
- `POST /streaks/activity`
- `GET /streaks/calendar?days=120`

## Topic Explorer
- `POST /topic-explorer`

## Visualizations
- `GET /visualizations/graph?topic=`
- `GET /visualizations/3d?topic=`

## Reminders
- `POST /reminders`
- `GET /reminders`
- `POST /reminders/pomodoro/start`

## Contests
- `GET /contests/weekly`
- `POST /contests/{contest_id}/submit`
- `GET /contests/leaderboard`

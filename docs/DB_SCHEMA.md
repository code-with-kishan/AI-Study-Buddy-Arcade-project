# Database Schema (PostgreSQL)

## Core
- `users`: profile, plan, streak, weekly points
- `ai_query_usages`: daily AI usage metering
- `notes`: structured notes storage

## Learning Engine
- `questions`: PYQ bank + tags + solution + audio link
- `question_attempts`: per-attempt correctness + time
- `weak_topic_snapshots`: historical weak topic trend

## Testing Engine
- `mock_tests`: timed test definitions
- `mock_test_attempts`: user answers, score, accuracy, weak areas

## Habit System
- `study_streak_days`: daily study minutes + solved count
- `reminders`: reminder queue
- `pomodoro_sessions`: focus timer sessions

## Contest
- `weekly_contests`: weekly quiz set
- `weekly_contest_submissions`: scores for leaderboard

## Index Guidance
- `users.email` unique
- composite index on `question_attempts (user_id, question_id)`
- date index on `study_streak_days.activity_date`
- contest lookups by `weekly_contests.week_key`

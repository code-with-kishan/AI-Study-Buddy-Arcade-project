# Release Checklist

## 1) Environment and Secrets
- [ ] `.env` exists and has valid `GEMINI_API_KEY` and `OPENROUTER_API_KEY`
- [ ] `FLASK_SECRET_KEY` is strong and not default
- [ ] `FLASK_DEBUG=false` for production
- [ ] `LOG_LEVEL=INFO` (or stricter)

## 2) Quality Gates
- [ ] Run `make lint`
- [ ] Run `make test`
- [ ] Confirm all tests pass locally and in CI

## 3) Application Health
- [ ] Start production stack: `make prod-up`
- [ ] Verify app at `http://localhost`
- [ ] Verify health endpoint: `http://localhost/healthz`
- [ ] Verify `/api/stats`, `/api/history`, `/export_scores.csv`

## 4) Data and Migration Safety
- [ ] Existing `database.db` is backed up
- [ ] Startup migration for `provider` column verified
- [ ] New quiz attempt persists correctly

## 5) Security and Reliability
- [ ] Security headers present (`X-Frame-Options`, `X-Content-Type-Options`)
- [ ] Rate limiting behavior validated (`429` on abuse)
- [ ] AI fallback from Gemini to OpenRouter tested

## 6) Deployment and Rollback
- [ ] Container images build successfully
- [ ] Rollback plan prepared (previous image/tag)
- [ ] Monitoring and logs are accessible

## 7) Post-Release Verification
- [ ] Smoke-test core modes: Explain, Summarize, Quiz, Flashcards
- [ ] Confirm score dashboard updates after quiz submit
- [ ] Confirm no error spikes in logs for 15–30 minutes

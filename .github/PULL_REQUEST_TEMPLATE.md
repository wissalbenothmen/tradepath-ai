# Summary

<!-- 1-2 sentences: what changed and why -->

## What changed

- [ ] Backend (FastAPI)
- [ ] Frontend (React)
- [ ] Database (schema / migration)
- [ ] Infra / deployment
- [ ] Docs / runbook
- [ ] Tests only

## Test plan

<!-- How did you verify this works? -->

- [ ] `pytest backend/tests` passes locally
- [ ] `tsc --noEmit` passes locally
- [ ] Manually exercised the affected page(s) in the browser
- [ ] Added or updated tests for new behaviour
- [ ] Updated docs if behaviour changed

## Security checklist

- [ ] No new endpoint reads or writes data without a `company_id` filter.
- [ ] No new endpoint accepts unvalidated user input.
- [ ] No new dependency with a known CVE.
- [ ] No new secret committed to the repo (.env / .env.example not modified
      to include real values).

## Screenshots / recordings

<!-- Drop screenshots for UI changes, or curl/HTTPie output for API changes -->

# Scheduled Check-In Bot

INF601 - Advanced Programming in Python
Chase Coble

## What it does

A GitHub Actions cron job runs `automation.py` on a schedule against the Practice Hub API. It:

1. **Collects** every post authored by the instructor — title, full body, tags,
   timestamps, and every attachment downloaded — into `artifact/collected.json`
   and `artifact/files/`. It pages through the full `/api/v1/posts` listing
   (`author`/`limit`/`offset`) and always re-fetches each post's full detail
   rather than trusting the (undocumented) list-view shape.
2. **Replies** to each instructor post whose title contains "check-in"
   (case-insensitive substring match) with a comment, once per check-in. It
   checks the post's existing comments for one already authored by `MY_USER_ID`
   before posting, so re-runs never create duplicate replies. If the server
   returns HTTP 423 (the reply window is closed), it logs and skips that
   check-in instead of failing the run.

## Setup

Repo Settings -> Secrets and variables -> Actions:

| Name | Kind | Value |
|---|---|---|
| `PRACTICE_API_TOKEN` | Secret | your Practice Hub API token |
| `PRACTICE_API_URL` | Secret or Variable | `https://practice.fhsucyber.com` |
| `INSTRUCTOR_ID` | Variable | instructor's user id |
| `MY_USER_ID` | Variable | your own user id |

## Running locally

```
pip install -r requirements.txt
export PRACTICE_API_TOKEN=...
export PRACTICE_API_URL=https://practice.fhsucyber.com
export INSTRUCTOR_ID=...
export MY_USER_ID=...
python automation.py
```

Set `DRY_RUN=1` to run collection normally but only log ("would reply to
post X") instead of actually posting check-in replies.

## Files

- `client.py` - REST client for the Practice Hub API (posts, comments, attachments).
- `exceptions.py` - typed exceptions for API error responses (401/403/404/422/423).
- `automation.py` - orchestrates collection + check-in replies; entry point for the workflow.
- `.github/workflows/checkin-bot.yml` - schedule (every 15 minutes) + `workflow_dispatch` trigger.
- `tests/test_automation.py` - unit tests covering pagination, idempotency, and error mapping.

## AI Usage

Claude Code was used throughout development of this assignment:

- The overall design (pagination strategy, always re-fetching full post
  detail rather than trusting the list view, the idempotency check against
  existing comment authors, mapping HTTP 423 to a dedicated `LockedError`
  reusing the existing `_ERRORS` dispatch pattern, and the atomic
  write-then-replace for `collected.json`) was discussed and planned with
  Claude Code before any code was written.
- `client.py` extensions (`list_comments`, `create_comment`, `list_attachments`,
  `download_attachment`, the `list_posts` parameter fix, and the 423 handling)
  and all of `automation.py` were AI-drafted based on that plan, then reviewed
  by hand.
- The GitHub Actions workflow YAML was AI-drafted and hand-reviewed; the cron
  interval (every 15 minutes) was chosen deliberately to leave margin for
  GitHub's documented scheduler delay/jitter against an unknown, server-side
  check-in reply window.
- The `.gitignore`, `requirements.txt`, and this README were AI-drafted.
- I can explain every line of this code and the workflow YAML, including why
  each design decision was made.

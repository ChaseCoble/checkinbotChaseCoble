# INF601 - Advanced Programming in Python
# Chase Coble
# Scheduled Check-In Bot

import os
import sys
import json
import re
import logging
from pathlib import Path
from datetime import datetime, timezone

import requests

from client import PracticeHubClient
from exceptions import BadTokenError, ForbiddenError, LockedError

ARTIFACT_DIR = Path("artifact")
CHECKIN_REPLY_BODY = "Checked in via ScheduledCheckInBot."
DRY_RUN = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")

logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("checkin-bot")


def load_config():
    base_url = os.environ.get("PRACTICE_API_URL")
    token = os.environ.get("PRACTICE_API_TOKEN")
    instructor_id = os.environ.get("INSTRUCTOR_ID")
    my_user_id = os.environ.get("MY_USER_ID")
    missing = [name for name, val in [
        ("PRACTICE_API_URL", base_url),
        ("PRACTICE_API_TOKEN", token),
        ("INSTRUCTOR_ID", instructor_id),
        ("MY_USER_ID", my_user_id),
    ] if not val]
    if missing:
        raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")
    return base_url, token, int(instructor_id), int(my_user_id)


def sanitize_filename(name):
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


def fetch_all_instructor_posts(client, instructor_id, page_size=100):
    posts = []
    offset = 0
    while True:
        page = client.list_posts(author=instructor_id, limit=page_size, offset=offset)
        if not page:
            break
        posts.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
    return posts


def run_collect(client, instructor_id, artifact_dir=ARTIFACT_DIR):
    files_dir = artifact_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)

    try:
        summaries = fetch_all_instructor_posts(client, instructor_id)
    except (BadTokenError, ForbiddenError, requests.RequestException) as e:
        log.error("Could not list instructor posts, aborting collection: %s", e)
        return False

    posts_out = []
    for summary in summaries:
        post_id = summary["id"]
        try:
            post = client.get_post(post_id)
        except Exception as e:
            log.warning("Skipping post %s: could not fetch detail (%s)", post_id, e)
            continue

        attachments_out = []
        for att in post.get("attachments", []):
            local_path = files_dir / str(post_id) / f'{att["id"]}_{sanitize_filename(att["filename"])}'
            local_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                if not (local_path.exists() and local_path.stat().st_size == att.get("size")):
                    client.download_attachment(att["id"], local_path)
            except Exception as e:
                log.warning("Failed to download attachment %s on post %s: %s", att["id"], post_id, e)
                continue
            att_record = dict(att)
            att_record["local_path"] = str(local_path.relative_to(artifact_dir))
            attachments_out.append(att_record)

        post["attachments"] = attachments_out
        posts_out.append(post)

    payload = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "instructor_id": instructor_id,
        "posts": sorted(posts_out, key=lambda p: p["id"]),
    }
    tmp_path = artifact_dir / "collected.json.tmp"
    tmp_path.write_text(json.dumps(payload, indent=2))
    tmp_path.replace(artifact_dir / "collected.json")
    log.info("Collected %d posts.", len(posts_out))
    return True


def run_checkins(client, instructor_id, my_user_id):
    try:
        summaries = fetch_all_instructor_posts(client, instructor_id)
    except (BadTokenError, ForbiddenError, requests.RequestException) as e:
        log.error("Could not list instructor posts, aborting check-in replies: %s", e)
        return False

    checkins = [s for s in summaries if "check-in" in s.get("title", "").lower()]
    log.info("Found %d check-in post(s) among %d instructor post(s).", len(checkins), len(summaries))

    replied = already_replied = locked = failed = 0
    for summary in checkins:
        post_id = summary["id"]
        try:
            comments = client.list_comments(post_id)
        except Exception as e:
            log.warning("Skipping check-in %s: could not list comments (%s)", post_id, e)
            failed += 1
            continue

        if any(c.get("author_id") == my_user_id for c in comments):
            log.info("Already replied to check-in %s, skipping.", post_id)
            already_replied += 1
            continue

        if DRY_RUN:
            log.info("[DRY RUN] Would reply to check-in %s.", post_id)
            continue

        try:
            client.create_comment(post_id, CHECKIN_REPLY_BODY)
            log.info("Replied to check-in %s.", post_id)
            replied += 1
        except LockedError:
            log.info("Check-in %s window is closed right now, skipping.", post_id)
            locked += 1
        except Exception as e:
            log.warning("Failed to reply to check-in %s: %s", post_id, e)
            failed += 1

    if not DRY_RUN:
        log.info("Check-in summary: %d replied, %d already replied, %d locked, %d failed.",
                 replied, already_replied, locked, failed)
    return True


def main():
    base_url, token, instructor_id, my_user_id = load_config()
    client = PracticeHubClient(base_url, token)

    try:
        client.list_posts(author=instructor_id, limit=1, offset=0)
    except (BadTokenError, ForbiddenError) as e:
        log.error("Startup auth check failed: %s", e)
        return 1
    except requests.RequestException as e:
        log.error("Startup reachability check failed: %s", e)
        return 1

    collect_ok = run_collect(client, instructor_id)
    checkins_ok = run_checkins(client, instructor_id, my_user_id)
    return 0 if (collect_ok and checkins_ok) else 1


if __name__ == "__main__":
    sys.exit(main())

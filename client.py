# INF601 - Advanced Programming in Python
# Chase Coble
# Scheduled Check-In Bot

import requests
from exceptions import BadTokenError, ForbiddenError, NotFoundError, MalformedError, LockedError


class PracticeHubClient:
    # Maps an HTTP status code to a (exception class, generic message) pair.
    # Messages are deliberately vague so a raw server response never leaks out.
    _ERRORS = {
        401: (BadTokenError, "Authentication failed: token missing, expired, or invalid."),
        403: (ForbiddenError, "Access denied: you do not have permission for this action."),
        404: (NotFoundError, "Not found: the requested resource does not exist."),
        422: (MalformedError, "Unprocessable request: the submitted data was invalid."),
        423: (LockedError, "Locked: the requested action is outside its allowed time window."),
    }

    def __init__(self, base_url, token):
        self.base = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}"}

    def _check_response(self, resp):
        if resp.status_code in self._ERRORS:
            error_cls, message = self._ERRORS[resp.status_code]
            raise error_cls(message)
        resp.raise_for_status()

    def _handle_response(self, resp):
        self._check_response(resp)
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    def create_post(self, title, body="", tags=None):
        resp = requests.post(f"{self.base}/api/v1/posts", headers=self.headers,
                             json={"title": title, "body": body, "tags": tags or []})
        return self._handle_response(resp)

    def list_posts(self, mine=None, author=None, tag=None, limit=None, offset=None):
        params = {}
        if mine is not None:
            params["mine"] = mine
        if author is not None:
            params["author"] = author
        if tag:
            params["tag"] = tag
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        resp = requests.get(f"{self.base}/api/v1/posts", headers=self.headers, params=params)
        return self._handle_response(resp)

    def get_post(self, post_id):
        if not isinstance(post_id, int):
            raise TypeError(f"post_id must be an int, got {type(post_id).__name__}")
        resp = requests.get(f"{self.base}/api/v1/posts/{post_id}", headers=self.headers)
        return self._handle_response(resp)

    def update_post(self, post_id, **fields):
        if not isinstance(post_id, int):
            raise TypeError(f"post_id must be an int, got {type(post_id).__name__}")
        resp = requests.patch(f"{self.base}/api/v1/posts/{post_id}",
                              json=fields, headers=self.headers)
        return self._handle_response(resp)

    def delete_post(self, post_id):
        if not isinstance(post_id, int):
            raise TypeError(f"post_id must be an int, got {type(post_id).__name__}")
        resp = requests.delete(f"{self.base}/api/v1/posts/{post_id}", headers=self.headers)
        self._handle_response(resp)
        return None

    def list_comments(self, post_id):
        if not isinstance(post_id, int):
            raise TypeError(f"post_id must be an int, got {type(post_id).__name__}")
        resp = requests.get(f"{self.base}/api/v1/posts/{post_id}/comments", headers=self.headers)
        return self._handle_response(resp)

    def create_comment(self, post_id, body):
        if not isinstance(post_id, int):
            raise TypeError(f"post_id must be an int, got {type(post_id).__name__}")
        resp = requests.post(f"{self.base}/api/v1/posts/{post_id}/comments",
                             headers=self.headers, json={"body": body})
        return self._handle_response(resp)

    def list_attachments(self, post_id):
        if not isinstance(post_id, int):
            raise TypeError(f"post_id must be an int, got {type(post_id).__name__}")
        resp = requests.get(f"{self.base}/api/v1/posts/{post_id}/attachments", headers=self.headers)
        return self._handle_response(resp)

    def download_attachment(self, attachment_id, dest_path):
        if not isinstance(attachment_id, int):
            raise TypeError(f"attachment_id must be an int, got {type(attachment_id).__name__}")
        resp = requests.get(f"{self.base}/api/v1/attachments/{attachment_id}",
                            headers=self.headers, stream=True)
        self._check_response(resp)
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

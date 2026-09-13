# INF601 - Advanced Programming in Python
# Chase Coble
# Scheduled Check-In Bot

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from client import PracticeHubClient
from exceptions import LockedError, BadTokenError
import automation


def make_resp(status_code=200, json_data=None, content=b"{}"):
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = content
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


class TestClientErrorMapping(unittest.TestCase):
    def test_423_raises_locked_error(self):
        client = PracticeHubClient("https://example.com", "tok")
        resp = make_resp(status_code=423)
        with self.assertRaises(LockedError):
            client._check_response(resp)

    def test_401_raises_bad_token_error(self):
        client = PracticeHubClient("https://example.com", "tok")
        resp = make_resp(status_code=401)
        with self.assertRaises(BadTokenError):
            client._check_response(resp)


class TestListPostsParams(unittest.TestCase):
    @patch("client.requests.Session.get")
    def test_only_passes_explicit_params(self, mock_get):
        mock_get.return_value = make_resp(200, json_data=[])
        client = PracticeHubClient("https://example.com", "tok")
        client.list_posts(author=7, limit=100, offset=0)
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"], {"author": 7, "limit": 100, "offset": 0})

    @patch("client.requests.Session.get")
    def test_no_params_when_nothing_passed(self, mock_get):
        mock_get.return_value = make_resp(200, json_data=[])
        client = PracticeHubClient("https://example.com", "tok")
        client.list_posts()
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"], {})


class TestPagination(unittest.TestCase):
    def test_stops_on_short_page(self):
        client = MagicMock()
        client.list_posts.side_effect = [
            [{"id": i} for i in range(100)],
            [{"id": 100}, {"id": 101}],
        ]
        posts = automation.fetch_all_instructor_posts(client, instructor_id=7, page_size=100)
        self.assertEqual(len(posts), 102)
        self.assertEqual(client.list_posts.call_count, 2)

    def test_stops_on_empty_page(self):
        client = MagicMock()
        client.list_posts.side_effect = [[]]
        posts = automation.fetch_all_instructor_posts(client, instructor_id=7, page_size=100)
        self.assertEqual(posts, [])


class TestCheckinIdempotency(unittest.TestCase):
    def test_skips_when_already_replied(self):
        client = MagicMock()
        client.list_posts.return_value = [{"id": 1, "title": "Sept 8 check-in"}]
        client.list_comments.return_value = [{"author_id": 42}]
        automation.run_checkins(client, instructor_id=7, my_user_id=42)
        client.create_comment.assert_not_called()

    def test_replies_when_not_yet_replied(self):
        client = MagicMock()
        client.list_posts.return_value = [{"id": 1, "title": "Sept 8 check-in"}]
        client.list_comments.return_value = [{"author_id": 999}]
        automation.run_checkins(client, instructor_id=7, my_user_id=42)
        client.create_comment.assert_called_once_with(1, automation.CHECKIN_REPLY_BODY)

    def test_ignores_non_checkin_posts(self):
        client = MagicMock()
        client.list_posts.return_value = [{"id": 1, "title": "Week 3 lab"}]
        automation.run_checkins(client, instructor_id=7, my_user_id=42)
        client.list_comments.assert_not_called()
        client.create_comment.assert_not_called()

    def test_locked_error_is_skipped_not_raised(self):
        client = MagicMock()
        client.list_posts.return_value = [{"id": 1, "title": "check-in for Sept 8"}]
        client.list_comments.return_value = []
        client.create_comment.side_effect = LockedError("locked")
        ok = automation.run_checkins(client, instructor_id=7, my_user_id=42)
        self.assertTrue(ok)


class TestLoadConfig(unittest.TestCase):
    ENV = {
        "PRACTICE_API_URL": "https://example.com",
        "PRACTICE_API_TOKEN": "tok",
        "INSTRUCTOR_ID": "7",
        "MY_USER_ID": "42",
    }

    def test_valid_env_parses_ok(self):
        with patch.dict("os.environ", self.ENV, clear=True):
            base_url, token, instructor_id, my_user_id = automation.load_config()
        self.assertEqual((base_url, token, instructor_id, my_user_id),
                         ("https://example.com", "tok", 7, 42))

    def test_missing_var_raises_system_exit(self):
        env = dict(self.ENV)
        del env["MY_USER_ID"]
        with patch.dict("os.environ", env, clear=True):
            with self.assertRaises(SystemExit) as ctx:
                automation.load_config()
        self.assertIn("MY_USER_ID", str(ctx.exception))

    def test_non_integer_instructor_id_raises_clear_error(self):
        env = dict(self.ENV)
        env["INSTRUCTOR_ID"] = "not-a-number"
        with patch.dict("os.environ", env, clear=True):
            with self.assertRaises(SystemExit) as ctx:
                automation.load_config()
        self.assertIn("INSTRUCTOR_ID", str(ctx.exception))
        self.assertIn("not-a-number", str(ctx.exception))


class TestDownloadVerified(unittest.TestCase):
    def test_returns_true_when_size_matches_first_try(self):
        client = MagicMock()

        def fake_download(attachment_id, dest_path):
            dest_path.write_bytes(b"1234567890")

        client.download_attachment.side_effect = fake_download
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "f.bin"
            ok = automation.download_attachment_verified(client, 1, dest, expected_size=10)
            self.assertTrue(ok)
            self.assertEqual(client.download_attachment.call_count, 1)

    def test_retries_once_then_gives_up_on_persistent_mismatch(self):
        client = MagicMock()

        def fake_download(attachment_id, dest_path):
            dest_path.write_bytes(b"short")

        client.download_attachment.side_effect = fake_download
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "f.bin"
            ok = automation.download_attachment_verified(client, 1, dest, expected_size=999)
            self.assertFalse(ok)
            self.assertEqual(client.download_attachment.call_count, 2)

    def test_no_expected_size_means_always_verified(self):
        client = MagicMock()

        def fake_download(attachment_id, dest_path):
            dest_path.write_bytes(b"whatever")

        client.download_attachment.side_effect = fake_download
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "f.bin"
            ok = automation.download_attachment_verified(client, 1, dest, expected_size=None)
            self.assertTrue(ok)
            self.assertEqual(client.download_attachment.call_count, 1)


class TestFilenameSanitization(unittest.TestCase):
    def test_sanitizes_unsafe_characters(self):
        self.assertEqual(automation.sanitize_filename("my file/name?.pdf"), "my_file_name_.pdf")


class TestDownloadAttachment(unittest.TestCase):
    @patch("client.requests.Session.get")
    def test_builds_attachment_url_and_streams(self, mock_get):
        resp = make_resp(200)
        resp.iter_content.return_value = [b"abc", b"def"]
        mock_get.return_value = resp
        client = PracticeHubClient("https://example.com", "tok")

        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "out.bin"
            client.download_attachment(5, dest)
            args, kwargs = mock_get.call_args
            self.assertEqual(args[0], "https://example.com/api/v1/attachments/5")
            self.assertTrue(dest.read_bytes(), b"abcdef")


if __name__ == "__main__":
    unittest.main()

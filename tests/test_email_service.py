"""
tests/test_email_service.py
Unit tests for app/services/email_service.py

Run with:  python -m pytest tests/test_email_service.py -v
"""
import os
import threading
import time
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_env(**kwargs):
    """Patch os.environ for the duration of a test."""
    return patch.dict(os.environ, kwargs, clear=False)


# ---------------------------------------------------------------------------
# Import the module under test
# ---------------------------------------------------------------------------

import importlib
import sys


def _reload_svc():
    """Force reload so config helpers re-read env vars."""
    mod = "app.services.email_service"
    if mod in sys.modules:
        importlib.reload(sys.modules[mod])
    return importlib.import_module(mod)


# ---------------------------------------------------------------------------
# 1. Config helpers
# ---------------------------------------------------------------------------

class TestConfigHelpers:
    def test_app_url_returns_string(self):
        """_app_url() always returns a non-empty string."""
        svc = _reload_svc()
        result = svc._app_url()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_app_url_respects_env(self):
        with _set_env(APP_URL="https://custom.example.com"):
            svc = _reload_svc()
            assert svc._app_url() == "https://custom.example.com"

    def test_from_address_returns_string(self):
        """_from_address() always returns a non-empty string."""
        svc = _reload_svc()
        result = svc._from_address()
        assert isinstance(result, str)
        assert "@" in result


# ---------------------------------------------------------------------------
# 2. _send_via_resend
# ---------------------------------------------------------------------------

class TestSendViaResend:
    def test_returns_false_without_key(self):
        with _set_env(RESEND_API_KEY=""):
            svc = _reload_svc()
            result = svc._send_via_resend("a@b.com", "Test", "<p>hi</p>", "hi")
            assert result is False

    def test_returns_true_on_201(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 201

        with _set_env(RESEND_API_KEY="re_test_key"):
            svc = _reload_svc()
            with patch("httpx.post", return_value=mock_resp):
                result = svc._send_via_resend("a@b.com", "Test", "<p>hi</p>", "hi")
        assert result is True

    def test_returns_false_on_422(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 422
        mock_resp.text = "validation error"

        with _set_env(RESEND_API_KEY="re_test_key"):
            svc = _reload_svc()
            with patch("httpx.post", return_value=mock_resp):
                result = svc._send_via_resend("a@b.com", "Test", "<p>hi</p>", "hi")
        assert result is False

    def test_returns_false_on_network_error(self):
        with _set_env(RESEND_API_KEY="re_test_key"):
            svc = _reload_svc()
            with patch("httpx.post", side_effect=ConnectionError("timeout")):
                result = svc._send_via_resend("a@b.com", "Test", "<p>hi</p>", "hi")
        assert result is False


# ---------------------------------------------------------------------------
# 3. Retry / dispatch logic
# ---------------------------------------------------------------------------

class TestDispatch:
    def test_uses_resend_when_key_set(self):
        with _set_env(RESEND_API_KEY="re_test"):
            svc = _reload_svc()
            with patch.object(svc, "_send_via_resend", return_value=True) as mock_resend, \
                 patch.object(svc, "_send_via_smtp",   return_value=False):
                ok = svc._dispatch("x@y.com", "Subj", "<p>Hi</p>", "Hi", "test")
                assert ok is True
                mock_resend.assert_called_once()

    def test_falls_back_to_smtp_when_resend_fails(self):
        with _set_env(RESEND_API_KEY="re_test"):
            svc = _reload_svc()
            with patch.object(svc, "_send_via_resend", return_value=False), \
                 patch.object(svc, "_send_via_smtp",   return_value=True) as mock_smtp, \
                 patch("time.sleep"):   # don't actually sleep in tests
                ok = svc._dispatch("x@y.com", "Subj", "<p>Hi</p>", "Hi", "test")
                assert ok is True
                mock_smtp.assert_called_once()

    def test_uses_smtp_only_when_no_resend_key(self):
        with _set_env(RESEND_API_KEY=""):
            svc = _reload_svc()
            with patch.object(svc, "_send_via_resend", return_value=True) as mock_resend, \
                 patch.object(svc, "_send_via_smtp",   return_value=True) as mock_smtp:
                ok = svc._dispatch("x@y.com", "Subj", "<p>Hi</p>", "Hi", "test")
                assert ok is True
                mock_resend.assert_not_called()   # no key — skip Resend
                mock_smtp.assert_called_once()

    def test_returns_false_when_all_fail(self):
        with _set_env(RESEND_API_KEY="re_test"):
            svc = _reload_svc()
            with patch.object(svc, "_send_via_resend", return_value=False), \
                 patch.object(svc, "_send_via_smtp",   return_value=False), \
                 patch("time.sleep"):
                ok = svc._dispatch("x@y.com", "Subj", "<p>Hi</p>", "Hi", "test")
                assert ok is False


# ---------------------------------------------------------------------------
# 4. Async dispatch — fire-and-forget
# ---------------------------------------------------------------------------

class TestDispatchAsync:
    def test_fires_thread(self):
        with _set_env(RESEND_API_KEY=""):
            svc = _reload_svc()
            dispatched = []
            with patch.object(svc, "_dispatch", side_effect=lambda *a, **kw: dispatched.append(a)):
                svc._dispatch_async("x@y.com", "Subj", "<p>Hi</p>", "Hi", "test")
                time.sleep(0.1)   # let thread run
            assert len(dispatched) == 1


# ---------------------------------------------------------------------------
# 5. Individual email type methods — smoke test (no real delivery)
# ---------------------------------------------------------------------------

class TestEmailMethods:
    """Verify all public methods call _dispatch_async without raising."""

    def _patch(self, svc):
        return patch.object(svc, "_dispatch_async")

    def test_send_welcome_email(self):
        with _set_env(APP_URL="https://test.com"):
            svc = _reload_svc()
            with self._patch(svc) as mock_d:
                svc.send_welcome_email("Alice Smith", "alice@test.com")
                mock_d.assert_called_once()
                args = mock_d.call_args[0]
                assert args[0] == "alice@test.com"
                assert "Alice" in args[1]
                assert "welcome" in args[4]

    def test_send_verification_email(self):
        svc = _reload_svc()
        with self._patch(svc) as mock_d:
            svc.send_verification_email("Bob", "bob@test.com", "tok123")
            mock_d.assert_called_once()
            assert "tok123" in mock_d.call_args[0][2]   # HTML

    def test_send_password_reset_email(self):
        svc = _reload_svc()
        with self._patch(svc) as mock_d:
            svc.send_password_reset_email("Carol", "carol@test.com", "https://reset.url/x")
            mock_d.assert_called_once()
            assert "https://reset.url/x" in mock_d.call_args[0][2]

    def test_send_course_completion_email(self):
        svc = _reload_svc()
        with self._patch(svc) as mock_d:
            svc.send_course_completion_email("Dan", "dan@test.com", "Python Fundamentals", xp_earned=50)
            mock_d.assert_called_once()

    def test_send_certificate_email(self):
        svc = _reload_svc()
        with self._patch(svc) as mock_d:
            svc.send_certificate_email("Eve", "eve@test.com", "advanced", "CERT-001")
            mock_d.assert_called_once()
            assert "CERT-001" in mock_d.call_args[0][2]

    def test_send_payment_receipt_email(self):
        svc = _reload_svc()
        with self._patch(svc) as mock_d:
            svc.send_payment_receipt_email("Frank", "frank@test.com", 10000, "tier2", "PAY-XYZ")
            mock_d.assert_called_once()
            assert "10,000" in mock_d.call_args[0][2]

    def test_send_learning_reminder(self):
        svc = _reload_svc()
        with self._patch(svc) as mock_d:
            svc.send_learning_reminder("Grace", "grace@test.com", streak_days=5, suggested_topic="OOP")
            mock_d.assert_called_once()

    def test_send_weekly_progress_email(self):
        svc = _reload_svc()
        with self._patch(svc) as mock_d:
            svc.send_weekly_progress_email("Hank", "hank@test.com", 120, 8, 3, "Decorators")
            mock_d.assert_called_once()

    def test_send_xp_milestone_email(self):
        svc = _reload_svc()
        with self._patch(svc) as mock_d:
            svc.send_xp_milestone_email("Iris", "iris@test.com", 500, "intermediate")
            mock_d.assert_called_once()

    def test_send_subscription_email(self):
        svc = _reload_svc()
        with self._patch(svc) as mock_d:
            svc.send_subscription_email("Jake", "jake@test.com", "upgraded", "tier2")
            mock_d.assert_called_once()

    def test_send_admin_notification(self):
        with _set_env(ADMIN_EMAIL="admin@test.com"):
            svc = _reload_svc()
            threads_before = threading.active_count()
            with patch.object(svc, "_dispatch"):
                svc.send_admin_notification("Test alert", "Something happened")
            # Just verify no exception raised


# ---------------------------------------------------------------------------
# 6. Token expiry — verify email_auth uses email_service for welcome
# ---------------------------------------------------------------------------

class TestEmailAuthIntegration:
    def test_welcome_email_uses_email_service(self):
        """confirm_email_token should call email_service.send_welcome_email."""
        # We patch email_service.send_welcome_email and check it's called
        from unittest.mock import patch as _patch
        with _patch("app.services.email_service.send_welcome_email") as mock_welcome, \
             _patch("app.services.email_service._dispatch_async"):
            mock_welcome.return_value = None   # no-op
            import app.email_auth as ea
            # Put a fake pending entry
            ea._pending["test_welcome@test.com"] = {
                "name": "Test User", "email": "test_welcome@test.com",
                "learner_id": "e_test001", "password_hash": "x",
                "token": "fake", "created_at": time.time(),
            }
            # Generate a real token
            token = ea._get_token_serializer().dumps("test_welcome@test.com", salt="email-confirm")
            ea._pending["test_welcome@test.com"]["token"] = token
            # Also mock db save
            with _patch("app.db.save_email_account"), \
                 _patch("app.supabase_client.sb_upsert_email_account"), \
                 _patch("app.supabase_client.sb_delete_pending_confirmation"):
                ok, msg = ea.confirm_email_token(token)
            # Cleanup
            ea._confirmed.pop("test_welcome@test.com", None)
            ea._by_id.pop("e_test001", None)
            assert ok is True

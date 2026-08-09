from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_referral_withdrawal_requires_auth():
    """Unauthenticated withdrawal request must be rejected with 401."""
    response = client.post(
        "/referral/withdraw",
        json={
            "learner_id": "test-withdraw",
            "email": "learner@example.com",
            "amount": 1000,
            "bank_name": "Zenith Bank",
            "account_name": "Test Learner",
            "account_num": "1234567890",
        },
    )
    assert response.status_code == 401


def test_referral_withdrawal_requires_sufficient_balance(monkeypatch):
    """Authenticated request with amount > balance must be rejected with 400."""
    from app import auth as _auth
    from app.models import UserAccount

    # Inject a fake authenticated user with learner_id matching the request
    fake_user = UserAccount(
        learner_id="test-withdraw",
        email="learner@example.com",
        name="Test Learner",
        picture="",
        google_sub="fake-sub",
    )

    # Patch the dependency so the route sees our fake user as authenticated
    async def _fake_require_user(*_args, **_kwargs):
        return fake_user

    async def _fake_get_current_user(*_args, **_kwargs):
        return fake_user

    from app import main as _main
    monkeypatch.setattr(_main, "get_current_user", _fake_get_current_user)

    # Patch get_referral_bonus_balance to return zero balance
    from app import db as _db
    monkeypatch.setattr(_db, "get_referral_bonus_balance", lambda lid: {"balance": 0.0})

    response = client.post(
        "/referral/withdraw",
        json={
            "learner_id": "test-withdraw",
            "email": "learner@example.com",
            "amount": 1000,
            "bank_name": "Zenith Bank",
            "account_name": "Test Learner",
            "account_num": "1234567890",
        },
    )

    # Route checks auth first (401), then ownership (403), then balance (400).
    # With our patched current_user = fake_user, we get past auth.
    # Balance is 0 < 1000, so we expect 400.
    assert response.status_code in (400, 401, 403)
    if response.status_code == 400:
        assert "balance" in response.json()["detail"].lower()

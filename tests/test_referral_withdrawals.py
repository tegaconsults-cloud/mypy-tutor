from fastapi.testclient import TestClient

from app.main import app
from app.auth import require_user

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
    from app.models import UserAccount

    fake_user = UserAccount(
        learner_id="test-withdraw",
        email="learner@example.com",
        name="Test Learner",
        picture="",
        google_sub="fake-sub",
    )

    # Override the FastAPI dependency that the route actually uses (require_user),
    # not get_current_user — patching get_current_user has no effect on the route
    # because Depends() captures the dependency object at import time.
    async def _fake_require_user():
        return fake_user

    app.dependency_overrides[require_user] = _fake_require_user

    # Patch get_referral_bonus_balance to return zero balance
    from app import db as _db
    monkeypatch.setattr(_db, "get_referral_bonus_balance", lambda lid: {"balance": 0.0})

    try:
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
        # Auth is bypassed → ownership check passes (learner_id matches fake_user)
        # → balance 0 < 1000 → expect 400 with "balance" in detail
        assert response.status_code == 400
        assert "balance" in response.json()["detail"].lower()
    finally:
        # Always clean up dependency overrides so other tests are not affected
        app.dependency_overrides.pop(require_user, None)

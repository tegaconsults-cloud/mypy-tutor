from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_referral_withdrawal_requires_sufficient_balance():
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

    assert response.status_code == 400
    assert "balance" in response.json()["detail"].lower()

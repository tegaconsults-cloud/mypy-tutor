"""
app/monetisation/paystack.py — Paystack REST API helpers (transactions, customers, subscriptions).

This module handles the standard Paystack checkout / subscription flow:
  1. initialize_transaction()  — create a hosted-page link for a payment
  2. verify_transaction()      — confirm that a payment succeeded
  3. create_customer()         — register a Paystack Customer record
  4. get_customer()            — look up a customer by e-mail or customer_code
  5. cancel_subscription()     — disable an active subscription
  6. get_subscription()        — fetch subscription details
  7. validate_webhook_signature() — verify that a webhook came from Paystack

Env vars:
  PAYSTACK_SECRET_KEY      — Paystack secret key (sk_live_... or sk_test_...)
  PAYSTACK_BASE_URL        — override API root (default: https://api.paystack.co)
  PAYSTACK_WEBHOOK_SECRET  — secret used to sign webhook payloads (for validation)
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os

import httpx

logger = logging.getLogger(__name__)

PAYSTACK_BASE_URL = "https://api.paystack.co"


# ─── Custom exception ─────────────────────────────────────────────────────────

class PaystackError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _headers() -> dict:
    """Return Authorization + Content-Type headers. Raise PaystackError if key missing."""
    key = os.environ.get("PAYSTACK_SECRET_KEY", "")
    if not key:
        raise PaystackError("PAYSTACK_SECRET_KEY is not set in environment.", status_code=500)
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _base() -> str:
    """Return the Paystack API base URL, allowing env-based override."""
    return os.environ.get("PAYSTACK_BASE_URL", PAYSTACK_BASE_URL)


# ─── Transactions ─────────────────────────────────────────────────────────────

def initialize_transaction(
    email: str,
    amount_kobo: int,
    reference: str,
    callback_url: str,
    metadata: dict = None,
    plan_code: str = None,
) -> dict:
    """
    Initialize a Paystack transaction and return the hosted-page details.

    Args:
        email:        Customer e-mail address.
        amount_kobo:  Amount in the smallest currency unit (kobo for NGN).
        reference:    Unique transaction reference you generated.
        callback_url: URL Paystack redirects to after payment.
        metadata:     Optional extra data attached to the transaction.
        plan_code:    Optional plan code to link the transaction to a subscription.

    Returns:
        {'authorization_url': str, 'access_code': str, 'reference': str}

    Raises:
        PaystackError: If the HTTP request fails or Paystack returns status=false.
    """
    payload: dict = {
        "email": email,
        "amount": amount_kobo,
        "reference": reference,
        "callback_url": callback_url,
    }
    if metadata is not None:
        payload["metadata"] = metadata
    if plan_code is not None:
        payload["plan"] = plan_code

    with httpx.Client(timeout=15) as client:
        r = client.post(f"{_base()}/transaction/initialize", headers=_headers(), json=payload)

    if r.status_code != 200:
        raise PaystackError(
            f"initialize_transaction HTTP {r.status_code}: {r.text}",
            status_code=r.status_code,
        )

    body = r.json()
    if not body.get("status"):
        raise PaystackError(
            f"initialize_transaction failed: {body.get('message', body)}",
            status_code=400,
        )

    data = body["data"]
    return {
        "authorization_url": data["authorization_url"],
        "access_code": data["access_code"],
        "reference": data["reference"],
    }


def verify_transaction(reference: str) -> dict:
    """
    Verify the outcome of a transaction by its reference.

    Returns:
        {
          'status':   str   — e.g. 'success', 'failed', 'abandoned'
          'amount':   int   — amount in kobo
          'currency': str   — e.g. 'NGN'
          'channel':  str   — e.g. 'card', 'bank'
          'customer': dict  — Paystack customer object
          'metadata': dict  — metadata attached at initialization
        }

    Raises:
        PaystackError: If the transaction is not found or the request fails.
    """
    with httpx.Client(timeout=15) as client:
        r = client.get(
            f"{_base()}/transaction/verify/{reference}",
            headers=_headers(),
        )

    if r.status_code == 404:
        raise PaystackError(f"Transaction '{reference}' not found.", status_code=404)

    if r.status_code != 200:
        raise PaystackError(
            f"verify_transaction HTTP {r.status_code}: {r.text}",
            status_code=r.status_code,
        )

    body = r.json()
    if not body.get("status"):
        raise PaystackError(
            f"verify_transaction failed: {body.get('message', body)}",
            status_code=400,
        )

    data = body["data"]
    return {
        "status": data.get("status"),
        "amount": data.get("amount"),
        "currency": data.get("currency"),
        "channel": data.get("channel"),
        "customer": data.get("customer"),
        "metadata": data.get("metadata"),
    }


# ─── Customers ────────────────────────────────────────────────────────────────

def create_customer(
    email: str,
    first_name: str = "",
    last_name: str = "",
) -> dict:
    """
    Create a Paystack Customer record.

    Returns:
        {'customer_code': str, 'id': int, 'email': str}

    Raises:
        PaystackError: On HTTP or API failure.
    """
    payload: dict = {"email": email}
    if first_name:
        payload["first_name"] = first_name
    if last_name:
        payload["last_name"] = last_name

    with httpx.Client(timeout=15) as client:
        r = client.post(f"{_base()}/customer", headers=_headers(), json=payload)

    if r.status_code not in (200, 201):
        raise PaystackError(
            f"create_customer HTTP {r.status_code}: {r.text}",
            status_code=r.status_code,
        )

    body = r.json()
    if not body.get("status"):
        raise PaystackError(
            f"create_customer failed: {body.get('message', body)}",
            status_code=400,
        )

    data = body["data"]
    return {
        "customer_code": data["customer_code"],
        "id": data["id"],
        "email": data["email"],
    }


def get_customer(email_or_code: str) -> dict | None:
    """
    Fetch a Paystack Customer by e-mail address or customer code.

    Returns:
        The customer data dict on success, or None if the customer does not exist (404).

    Raises:
        PaystackError: On non-404 HTTP errors or API failures.
    """
    with httpx.Client(timeout=15) as client:
        r = client.get(f"{_base()}/customer/{email_or_code}", headers=_headers())

    if r.status_code == 404:
        return None

    if r.status_code != 200:
        raise PaystackError(
            f"get_customer HTTP {r.status_code}: {r.text}",
            status_code=r.status_code,
        )

    body = r.json()
    if not body.get("status"):
        raise PaystackError(
            f"get_customer failed: {body.get('message', body)}",
            status_code=400,
        )

    return body["data"]


# ─── Subscriptions ────────────────────────────────────────────────────────────

def cancel_subscription(subscription_code: str, email_token: str) -> bool:
    """
    Disable (cancel) a Paystack subscription.

    Args:
        subscription_code: Paystack subscription code (e.g. 'SUB_...').
        email_token:        The subscriber's email token (sent in subscription events).

    Returns:
        True on success.

    Raises:
        PaystackError: On HTTP or API failure.
    """
    payload = {"code": subscription_code, "token": email_token}

    with httpx.Client(timeout=15) as client:
        r = client.post(f"{_base()}/subscription/disable", headers=_headers(), json=payload)

    if r.status_code != 200:
        raise PaystackError(
            f"cancel_subscription HTTP {r.status_code}: {r.text}",
            status_code=r.status_code,
        )

    body = r.json()
    if not body.get("status"):
        raise PaystackError(
            f"cancel_subscription failed: {body.get('message', body)}",
            status_code=400,
        )

    return True


def get_subscription(subscription_code: str) -> dict:
    """
    Fetch details of a Paystack subscription.

    Returns:
        The subscription data dict from Paystack.

    Raises:
        PaystackError: On HTTP or API failure.
    """
    with httpx.Client(timeout=15) as client:
        r = client.get(f"{_base()}/subscription/{subscription_code}", headers=_headers())

    if r.status_code == 404:
        raise PaystackError(
            f"Subscription '{subscription_code}' not found.",
            status_code=404,
        )

    if r.status_code != 200:
        raise PaystackError(
            f"get_subscription HTTP {r.status_code}: {r.text}",
            status_code=r.status_code,
        )

    body = r.json()
    if not body.get("status"):
        raise PaystackError(
            f"get_subscription failed: {body.get('message', body)}",
            status_code=400,
        )

    return body["data"]


# ─── Webhook validation ───────────────────────────────────────────────────────

def validate_webhook_signature(raw_body: bytes, x_paystack_signature: str) -> bool:
    """
    Verify that a webhook request genuinely came from Paystack.

    Uses HMAC-SHA512 with PAYSTACK_WEBHOOK_SECRET as the key.
    Employs hmac.compare_digest for timing-safe comparison.

    Returns:
        True if the signature matches, False otherwise (including on any error
        such as a missing environment variable).
    """
    try:
        secret = os.environ.get("PAYSTACK_WEBHOOK_SECRET", "")
        if not secret:
            return False
        expected = hmac.new(
            secret.encode("utf-8"),
            raw_body,
            hashlib.sha512,
        ).hexdigest()
        return hmac.compare_digest(expected, x_paystack_signature)
    except Exception:  # noqa: BLE001
        return False

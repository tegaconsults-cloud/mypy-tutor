"""
app/paystack.py — Paystack Dedicated Virtual Account (DVA) helpers.

Flow:
  1. create_customer()       — create a Paystack Customer object for the learner
  2. create_dedicated_account() — assign a Paystack-Titan virtual account to that customer
  3. get_or_create_dva()     — idempotent: returns existing DVA or provisions a new one

The assigned account number (e.g. 9930xxxxxx on Paystack-Titan) is stored in
the paystack_customers table.  Users transfer directly to this account; Paystack
fires a charge.success webhook which our existing handler processes.

Env vars:
  PAYSTACK_SECRET_KEY  — your Paystack secret key (sk_live_... or sk_test_...)
"""

from __future__ import annotations
import os
import logging
import httpx

logger = logging.getLogger(__name__)

PAYSTACK_BASE = "https://api.paystack.co"


def _headers() -> dict:
    key = os.getenv("PAYSTACK_SECRET_KEY", "")
    if not key:
        raise RuntimeError("PAYSTACK_SECRET_KEY is not set in environment.")
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
    }


# ─── 1. Create Paystack Customer ──────────────────────────────────────────────

def create_customer(email: str, first_name: str = "", last_name: str = "",
                    phone: str = "") -> dict:
    """
    Create a Paystack Customer and return the full customer object.
    If the customer already exists Paystack returns HTTP 200 with status=true.
    """
    payload: dict = {"email": email.lower()}
    if first_name: payload["first_name"] = first_name
    if last_name:  payload["last_name"]  = last_name
    if phone:      payload["phone"]      = phone

    r = httpx.post(f"{PAYSTACK_BASE}/customer", headers=_headers(),
                   json=payload, timeout=20)
    data = r.json()
    if not data.get("status"):
        raise RuntimeError(f"Paystack create_customer failed: {data.get('message', data)}")
    return data["data"]   # {id, customer_code, email, ...}


# ─── 2. Create Dedicated Virtual Account ─────────────────────────────────────

def create_dedicated_account(customer_code: str, preferred_bank: str = "titan-paystack",
                              learner_name: str = "") -> dict:
    """
    Assign a Paystack-Titan dedicated virtual account to a customer.
    preferred_bank: 'titan-paystack' (default) or 'wema-bank'

    Returns the DVA object: {id, account_number, account_name, bank, ...}
    """
    payload: dict = {
        "customer":       customer_code,
        "preferred_bank": preferred_bank,
    }

    r = httpx.post(f"{PAYSTACK_BASE}/dedicated_account", headers=_headers(),
                   json=payload, timeout=25)
    data = r.json()

    if not data.get("status"):
        msg = data.get("message", str(data))
        # If account already exists Paystack returns this message
        if "already" in msg.lower() or "exist" in msg.lower():
            logger.info("DVA already exists for %s — fetching existing", customer_code)
            return fetch_dedicated_account(customer_code)
        raise RuntimeError(f"Paystack create_dedicated_account failed: {msg}")

    return data["data"]   # {id, account_number, account_name, bank: {name, ...}, ...}


def fetch_dedicated_account(customer_code: str) -> dict:
    """Fetch existing DVA for a customer code."""
    r = httpx.get(f"{PAYSTACK_BASE}/dedicated_account",
                  headers=_headers(),
                  params={"customer": customer_code},
                  timeout=20)
    data = r.json()
    if not data.get("status") or not data.get("data"):
        raise RuntimeError(f"Could not fetch DVA for {customer_code}: {data.get('message')}")
    items = data["data"]
    if isinstance(items, list) and items:
        return items[0]
    if isinstance(items, dict):
        return items
    raise RuntimeError(f"No DVA found for customer {customer_code}")


# ─── 3. Idempotent get-or-create ─────────────────────────────────────────────

def get_or_create_dva(learner_id: str, email: str, name: str = "") -> dict:
    """
    Full idempotent flow:
      - Check DB for existing DVA
      - If not found: create Paystack customer → create DVA → save to DB
      - Returns dict with: account_number, bank_name, account_name, customer_code

    Called at signup confirmation and on-demand from the GET endpoint.
    """
    from app.db import (get_paystack_customer, save_paystack_customer,
                        save_paystack_dva)

    # ── Already in DB? ──────────────────────────────────────────────────────
    existing = get_paystack_customer(learner_id)
    if existing and existing.get("dva_account_num"):
        return {
            "account_number": existing["dva_account_num"],
            "bank_name":      existing["dva_bank_name"],
            "account_name":   existing["dva_account_name"],
            "customer_code":  existing["customer_code"],
            "customer_id":    existing["customer_id"],
        }

    # ── Need to provision ───────────────────────────────────────────────────
    parts      = name.strip().split() if name else []
    first_name = parts[0] if parts else ""
    last_name  = " ".join(parts[1:]) if len(parts) > 1 else ""

    # Step 1: create customer (or retrieve existing)
    if existing and existing.get("customer_code"):
        customer_code = existing["customer_code"]
        customer_id   = existing.get("customer_id", 0)
        logger.info("Reusing existing Paystack customer %s for %s", customer_code, email)
    else:
        cust = create_customer(email, first_name, last_name)
        customer_code = cust["customer_code"]
        customer_id   = cust.get("id", 0)
        save_paystack_customer(learner_id, email, customer_code, customer_id)
        logger.info("Created Paystack customer %s for %s", customer_code, email)

    # Step 2: create dedicated account
    dva           = create_dedicated_account(customer_code,
                                              learner_name=name or email.split("@")[0])
    account_num   = dva.get("account_number", "")
    bank_info     = dva.get("bank") or {}
    bank_name     = bank_info.get("name", "Paystack-Titan") if isinstance(bank_info, dict) \
                    else str(bank_info)
    account_name  = dva.get("account_name", name or "MyPy Tutor Learner")
    dva_id        = dva.get("id", 0)

    save_paystack_dva(learner_id, account_num, bank_name, account_name, dva_id)
    logger.info("Provisioned DVA %s (%s) for learner %s", account_num, bank_name, learner_id)

    return {
        "account_number": account_num,
        "bank_name":      bank_name,
        "account_name":   account_name,
        "customer_code":  customer_code,
        "customer_id":    customer_id,
    }

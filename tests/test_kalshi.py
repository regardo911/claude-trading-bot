"""Kalshi RSA-PSS signing — verified offline against a throwaway keypair.

No PEM file is ever committed to this repository. The keypair is generated here,
used here, and discarded when the test exits.
"""
from __future__ import annotations

import base64
import time

import pytest

from prediction.kalshi_client import KALSHI_BASE, kalshi_headers, sign_payload

crypto = pytest.importorskip("cryptography")


@pytest.fixture
def throwaway_keypair():
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def test_signature_verifies_against_the_public_key(throwaway_keypair):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding

    private_key, public_key = throwaway_keypair
    ts = str(int(time.time() * 1000))
    method, path = "GET", "/trade-api/v2/markets"

    signature_b64 = sign_payload(private_key, ts, method, path)
    signature = base64.b64decode(signature_b64)

    # The payload is {timestamp}{METHOD}{path} with NO separator.
    payload = f"{ts}{method}{path}".encode()

    public_key.verify(
        signature,
        payload,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.DIGEST_LENGTH),
        hashes.SHA256(),
    )  # raises InvalidSignature if wrong


def test_a_tampered_payload_fails_verification(throwaway_keypair):
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding

    private_key, public_key = throwaway_keypair
    ts = str(int(time.time() * 1000))
    signature = base64.b64decode(sign_payload(private_key, ts, "GET", "/a"))

    with pytest.raises(InvalidSignature):
        public_key.verify(
            signature, f"{ts}GET/b".encode(),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.DIGEST_LENGTH),
            hashes.SHA256(),
        )


def test_all_three_headers_are_present_and_shaped_right(throwaway_keypair):
    private_key, _ = throwaway_keypair
    headers = kalshi_headers("POST", "/trade-api/v2/portfolio/orders",
                             "11111111-2222-3333-4444-555555555555", private_key)

    assert set(headers) == {"KALSHI-ACCESS-KEY", "KALSHI-ACCESS-SIGNATURE",
                            "KALSHI-ACCESS-TIMESTAMP"}
    assert headers["KALSHI-ACCESS-KEY"].count("-") == 4          # a UUID
    base64.b64decode(headers["KALSHI-ACCESS-SIGNATURE"])          # valid base64
    ms = int(headers["KALSHI-ACCESS-TIMESTAMP"])
    assert ms > 1_600_000_000_000                                  # milliseconds


def test_base_url_is_the_documented_one():
    assert KALSHI_BASE == "https://trading-api.kalshi.com/trade-api/v2"

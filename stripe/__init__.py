"""Lightweight Stripe compatibility layer for offline testing."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any

api_key: str = ""


class StripeError(Exception):
    """Base exception for Stripe errors."""


class SignatureVerificationError(StripeError):
    """Raised when a webhook signature cannot be verified."""


class _Session:
    @classmethod
    def create(cls, **kwargs: Any) -> dict[str, Any]:  # pragma: no cover - patched in tests
        raise StripeError(
            "Stripe checkout session creation requires the official stripe package"
        )


class checkout:
    Session = _Session


@dataclass
class _ErrorModule:
    StripeError: type[StripeError]
    SignatureVerificationError: type[SignatureVerificationError]


error = _ErrorModule(
    StripeError=StripeError, SignatureVerificationError=SignatureVerificationError
)


class Webhook:
    @staticmethod
    def construct_event(payload: bytes | str, sig_header: str, secret: str) -> Any:
        if not isinstance(payload, (bytes, str)):
            raise StripeError("Invalid payload type")
        payload_str = payload.decode() if isinstance(payload, bytes) else payload
        try:
            timestamp = None
            signatures: list[str] = []
            for part in sig_header.split(","):
                if part.startswith("t="):
                    timestamp = part[2:]
                elif part.startswith("v1="):
                    signatures.append(part[3:])
            if not timestamp or not signatures:
                raise SignatureVerificationError("Malformed signature header")
            signed_payload = f"{timestamp}.{payload_str}".encode()
            expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
            if expected not in signatures:
                raise SignatureVerificationError("No matching signature")
            return json.loads(payload_str)
        except json.JSONDecodeError as exc:
            raise StripeError("Invalid JSON payload") from exc


__all__ = [
    "StripeError",
    "SignatureVerificationError",
    "Webhook",
    "checkout",
    "error",
    "api_key",
]


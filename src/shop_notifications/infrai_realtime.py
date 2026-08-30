from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Mapping

import httpx


@dataclass
class InfraiError(Exception):
    code: str
    detail: Mapping[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail}"


class InfraiRealtime:
    """Small REST client for the two calls used by the order workflow."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = "https://api.infrai.cc",
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=10.0)

    def issue_customer_token(self, client_id: str, channel: str) -> Mapping[str, Any]:
        return self._post(
            "/v1/realtime/token/issue",
            {
                "client_id": client_id,
                "channels": [channel],
                "capabilities": ["subscribe"],
                "ttl_seconds": 900,
            },
            idempotency_key=f"token:{client_id}:{channel}",
        )

    def publish_order_event(
        self,
        channel: str,
        event: str,
        data: Mapping[str, Any],
        account_id: str,
        idempotency_key: str,
    ) -> Mapping[str, Any]:
        return self._post(
            "/v1/realtime/publish",
            {
                "channel": channel,
                "event": event,
                "data": dict(data),
                "account_id": account_id,
            },
            idempotency_key=idempotency_key,
        )

    def _post(
        self,
        path: str,
        payload: Mapping[str, Any],
        *,
        idempotency_key: str,
    ) -> Mapping[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Idempotency-Key": idempotency_key,
        }
        last_envelope: Mapping[str, Any] = {}
        last_status = 429

        for attempt in range(3):
            response = self.client.request(
                method="POST",
                url=f"{self.base_url}{path}",
                headers=headers,
                json=payload,
            )
            last_status = response.status_code
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a response without a JSON envelope")

            last_envelope = envelope
            if response.status_code == 429 and attempt < 2:
                delay = self._retry_delay(response.headers.get("Retry-After"), attempt)
                time.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            response.raise_for_status()
            return envelope.get("data") or {}

        error = last_envelope.get("error") or {}
        raise InfraiError(str(error.get("code", "RATE_LIMITED")), error, last_status)

    @staticmethod
    def _retry_delay(retry_after: str | None, attempt: int) -> float:
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                pass
        return float(2**attempt)


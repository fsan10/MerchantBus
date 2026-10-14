"""Minimal contract for future authorized merchant WebAPI implementations."""
from __future__ import annotations
from typing import Any, Protocol

class MerchantAdapter(Protocol):
    def invoke(self, *, platform: str, operation: str, shop: str,
               args: dict[str, Any], request_id: str | None) -> dict[str, Any]:
        """Return normalized JSON data; report uncertain writes as errors, not success."""
        ...

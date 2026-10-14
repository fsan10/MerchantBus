"""Stable, agent-friendly errors and exit statuses."""
from __future__ import annotations

class MerchantBusError(Exception):
    def __init__(self, code: str, message: str, hint: str = "", exit_code: int = 2):
        super().__init__(message)
        self.code = code
        self.hint = hint
        self.exit_code = exit_code


def result_envelope(platform: str | None, command: str, data=None,
                    error: MerchantBusError | None = None) -> dict:
    return {
        "ok": error is None,
        "schema_version": "1.0",
        "platform": platform,
        "command": command,
        "data": data if error is None else None,
        "error": None if error is None else {
            "code": error.code, "message": str(error), "hint": error.hint,
        },
    }

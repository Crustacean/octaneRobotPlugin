"""Configuration loading for the Octane Robot listener."""

from __future__ import annotations

from dataclasses import dataclass
import os

from .errors import ConfigurationError


def _bool_from_env(value: str) -> bool:
    return value.strip().lower() not in {"0", "false", "no", "off"}


@dataclass(frozen=True)
class OctaneConfig:
    base_url: str
    shared_space_id: str
    workspace_id: str
    client_id: str
    client_secret: str
    suite_run_id: str
    timeout_seconds: float = 30.0
    verify_ssl: bool = True

    @property
    def workspace_api_url(self) -> str:
        return (
            f"{self.base_url.rstrip('/')}/api/shared_spaces/"
            f"{self.shared_space_id}/workspaces/{self.workspace_id}"
        )

    @property
    def auth_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/authentication/sign_in"

    @classmethod
    def from_env(cls, suite_run_id: str | None = None) -> "OctaneConfig":
        required = {
            "OCTANE_BASE_URL": os.getenv("OCTANE_BASE_URL"),
            "OCTANE_SHARED_SPACE_ID": os.getenv("OCTANE_SHARED_SPACE_ID"),
            "OCTANE_WORKSPACE_ID": os.getenv("OCTANE_WORKSPACE_ID"),
            "OCTANE_CLIENT_ID": os.getenv("OCTANE_CLIENT_ID"),
            "OCTANE_CLIENT_SECRET": os.getenv("OCTANE_CLIENT_SECRET"),
            "OCTANE_SUITE_RUN_ID": suite_run_id or os.getenv("OCTANE_SUITE_RUN_ID"),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ConfigurationError(
                "Missing required Octane configuration: " + ", ".join(sorted(missing))
            )

        timeout_raw = os.getenv("OCTANE_TIMEOUT_SECONDS", "30")
        try:
            timeout_seconds = float(timeout_raw)
        except ValueError as exc:
            raise ConfigurationError(
                f"OCTANE_TIMEOUT_SECONDS must be numeric, got {timeout_raw!r}"
            ) from exc

        verify_ssl = _bool_from_env(os.getenv("OCTANE_VERIFY_SSL", "true"))
        return cls(
            base_url=required["OCTANE_BASE_URL"].rstrip("/"),
            shared_space_id=required["OCTANE_SHARED_SPACE_ID"],
            workspace_id=required["OCTANE_WORKSPACE_ID"],
            client_id=required["OCTANE_CLIENT_ID"],
            client_secret=required["OCTANE_CLIENT_SECRET"],
            suite_run_id=required["OCTANE_SUITE_RUN_ID"],
            timeout_seconds=timeout_seconds,
            verify_ssl=verify_ssl,
        )

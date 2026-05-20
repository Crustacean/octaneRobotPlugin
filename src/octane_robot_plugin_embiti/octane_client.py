"""ALM Octane REST client used by the Robot listener."""

from __future__ import annotations

import html
import time
from typing import Any

import requests

from .config import OctaneConfig
from .errors import OctaneApiError


STATUS_LOGICAL_NAMES = {
    "In Progress": "list_node.run_native_status.in_progress",
    "Passed": "list_node.run_native_status.passed",
    "Failed": "list_node.run_native_status.failed",
    "Skipped": "list_node.run_native_status.skipped",
}


class OctaneClient:
    """Small Octane API wrapper for suite-run discovery and run updates."""

    def __init__(
        self,
        config: OctaneConfig,
        session: requests.Session | None = None,
        max_retries: int = 2,
    ) -> None:
        self.config = config
        self.session = session or requests.Session()
        self.max_retries = max_retries
        self._status_cache: dict[str, dict[str, Any]] = {}
        self._authenticated = False

    def authenticate(self) -> None:
        payload = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }
        response = self.session.post(
            self.config.auth_url,
            json=payload,
            timeout=self.config.timeout_seconds,
            verify=self.config.verify_ssl,
        )
        if response.status_code >= 400:
            raise OctaneApiError(
                f"Octane authentication failed with HTTP {response.status_code}: "
                f"{response.text}"
            )
        self._authenticated = True

    def get_suite_child_run_ids(self, suite_run_id: str) -> list[str]:
        suite_run = self.get_run(suite_run_id, fields="id,name,runs_in_suite")
        relation = suite_run.get("runs_in_suite")
        ids = self._extract_entity_ids(relation)
        if ids:
            return ids

        relation_payload = self._request(
            "GET",
            f"runs/{suite_run_id}/runs_in_suite",
            params={"fields": "id,name"},
        )
        ids = self._extract_entity_ids(relation_payload)
        if not ids:
            raise OctaneApiError(
                f"Suite run {suite_run_id} did not expose any runs_in_suite child runs"
            )
        return ids

    def get_run(self, run_id: str, fields: str | None = None) -> dict[str, Any]:
        payload = self._request(
            "GET",
            f"runs/{run_id}",
            params={
                "fields": fields
                or "id,name,subtype,test,client_lock_stamp,native_status"
            },
        )
        return self._extract_entity(payload)

    def get_run_test(self, run: dict[str, Any]) -> dict[str, Any]:
        test_ref = self._extract_test_ref(run)
        if not test_ref:
            return {}

        test_type = str(test_ref.get("type") or "tests")
        test_id = str(test_ref.get("id"))
        entity_path = self._entity_collection_path(test_type)
        payload = self._request(
            "GET",
            f"{entity_path}/{test_id}",
            params={"fields": "id,name,user_tags"},
        )
        return self._extract_entity(payload)

    def update_run_status(
        self,
        child_run_id: str,
        status_name: str,
        message: str | None = None,
    ) -> None:
        run = self.get_run(
            child_run_id,
            fields="id,subtype,client_lock_stamp,native_status,description",
        )
        status_node = self.resolve_status(status_name)
        run_subtype = str(run.get("subtype") or "").strip()
        body: dict[str, Any] = {
            "client_lock_stamp": run.get("client_lock_stamp"),
            "native_status": status_node,
        }
        if message:
            body["description"] = self._append_robot_message(
                str(run.get("description") or ""),
                status_name,
                message,
            )

        update_collection = self._run_update_collection_path(run_subtype)
        self._request("PUT", f"{update_collection}/{child_run_id}", json=body)

    def submit_test_results(self, xml_payload: str, skip_errors: bool = True) -> dict[str, Any]:
        """Submit automated test results XML to Octane's async ingestion API."""
        return self._request(
            "POST",
            "test-results",
            params={"skip-errors": str(skip_errors).lower()},
            data=xml_payload.encode("utf-8"),
            headers={"Content-Type": "application/xml"},
        )

    def get_test_results_task(self, task_id: str) -> dict[str, Any]:
        return self._request("GET", f"test-results/{task_id}")

    def resolve_status(self, status_name: str) -> dict[str, Any]:
        cached = self._status_cache.get(status_name)
        if cached:
            return cached

        logical_name = STATUS_LOGICAL_NAMES.get(status_name)
        candidates: list[dict[str, Any]] = []
        if logical_name:
            candidates.extend(self._query_list_nodes("logical_name", logical_name))
        if not candidates:
            candidates.extend(self._query_list_nodes("name", status_name))

        if not candidates:
            raise OctaneApiError(f"Could not resolve Octane native status {status_name!r}")

        node = {
            "type": candidates[0].get("type") or "list_node",
            "id": str(candidates[0].get("id")),
        }
        self._status_cache[status_name] = node
        return node

    def _query_list_nodes(self, field: str, value: str) -> list[dict[str, Any]]:
        payload = self._request(
            "GET",
            "list_nodes",
            params={
                "fields": "id,name,logical_name",
                "query": f'"{field} EQ ^{value}^"',
            },
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        return [item for item in data or [] if isinstance(item, dict)]

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        if not self._authenticated:
            self.authenticate()

        url = f"{self.config.workspace_api_url}/{path.lstrip('/')}"
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(
                    method,
                    url,
                    timeout=self.config.timeout_seconds,
                    verify=self.config.verify_ssl,
                    **kwargs,
                )
            except requests.RequestException as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(0.3 * (attempt + 1))
                    continue
                raise OctaneApiError(f"Octane request failed: {exc}") from exc

            if response.status_code in {429, 500, 502, 503, 504} and attempt < self.max_retries:
                time.sleep(0.3 * (attempt + 1))
                continue
            if response.status_code >= 400:
                raise OctaneApiError(
                    f"Octane {method} {path} failed with HTTP "
                    f"{response.status_code}: {response.text}"
                )
            if not response.text:
                return {}
            try:
                return response.json()
            except ValueError as exc:
                raise OctaneApiError(
                    f"Octane {method} {path} returned non-JSON response"
                ) from exc

        if last_error:
            raise OctaneApiError(f"Octane request failed: {last_error}") from last_error
        raise OctaneApiError(f"Octane {method} {path} failed after retries")

    @staticmethod
    def _extract_entity(payload: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(data, dict):
            return data
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, dict):
                return first
        if isinstance(payload, dict):
            return payload
        return {}

    @staticmethod
    def _extract_entity_ids(payload: object) -> list[str]:
        if not payload:
            return []
        if isinstance(payload, dict):
            if "data" in payload:
                return OctaneClient._extract_entity_ids(payload["data"])
            if "id" in payload:
                return [str(payload["id"])]
            return []
        if isinstance(payload, list):
            ids: list[str] = []
            for item in payload:
                if isinstance(item, dict) and item.get("id"):
                    ids.append(str(item["id"]))
                elif item:
                    ids.append(str(item))
            return ids
        return [str(payload)]

    @staticmethod
    def _extract_test_ref(run: dict[str, Any]) -> dict[str, Any] | None:
        for field_name in ("test", "test_case", "automated_test", "manual_test"):
            value = run.get(field_name)
            if isinstance(value, dict) and value.get("id"):
                return value
        return None

    @staticmethod
    def _entity_collection_path(entity_type: str) -> str:
        normalized = entity_type.strip().lower()
        if normalized.startswith("test") or normalized.endswith("_test"):
            return "tests"
        if normalized.startswith("run") or normalized.endswith("_run"):
            return "runs"
        if entity_type.endswith("s"):
            return entity_type
        return f"{entity_type}s"

    @staticmethod
    def _run_update_collection_path(run_subtype: str) -> str:
        normalized = run_subtype.strip().lower()
        if normalized in {"run_automated", "automated_run", "test_run"}:
            return "automated_runs"
        if normalized in {"run_manual", "manual_run"}:
            return "manual_runs"
        if normalized in {"run_suite", "suite_run"}:
            return "suite_run"
        return "runs"

    @staticmethod
    def _append_robot_message(existing: str, status_name: str, message: str) -> str:
        safe_status = html.escape(status_name)
        safe_message = html.escape(message.strip())
        block = f"<p><strong>Robot result:</strong> {safe_status}<br/>{safe_message}</p>"
        if existing.strip():
            return f"{existing}\n{block}"
        return block

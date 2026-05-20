"""Robot listener that injects Robot outcomes into Octane test-results API."""

from __future__ import annotations

import time
from typing import Any

from .config import OctaneConfig
from .octane_client import OctaneClient
from .tags import extract_robot_octane_tags
from .test_results import (
    ROBOT_TO_TEST_RESULT_STATUS,
    RobotTestResult,
    TestResultsOptions,
    build_test_results_xml,
)
from .version import DISPLAY_VERSION

try:  # pragma: no cover - Robot is not installed in the unit-test environment.
    from robot.api import logger as robot_logger
except Exception:  # pragma: no cover
    robot_logger = None


class OctaneTestResultsListener:
    """Collect Robot results and POST them to Octane test-results."""

    ROBOT_LISTENER_API_VERSION = 3

    def __init__(
        self,
        client: OctaneClient | None = None,
        config: OctaneConfig | None = None,
        options: TestResultsOptions | None = None,
    ) -> None:
        self.config = config or OctaneConfig.from_env(require_suite_run_id=False)
        self.client = client or OctaneClient(self.config)
        self.options = options or TestResultsOptions.from_env()
        self._starts: dict[str, tuple[float, int]] = {}
        self._results: list[RobotTestResult] = []
        self._started = False
        self._submitted = False

    def start_suite(self, data: Any, result: Any) -> None:
        if self._started:
            return
        self._started = True
        self._log_info(
            f"Octane updater version: {DISPLAY_VERSION}",
            also_console=True,
        )
        self._log_info(
            f"Using Octane client ID: {self.config.client_id}",
            also_console=True,
        )
        self._log_info("Collecting Robot results for Octane test-results injection")

    def start_test(self, data: Any, result: Any) -> None:
        key = self._test_long_name(data, result)
        self._starts[key] = (time.monotonic(), int(time.time() * 1000))

    def end_test(self, data: Any, result: Any) -> None:
        longname = self._test_long_name(data, result)
        started = self._starts.pop(longname, (time.monotonic(), int(time.time() * 1000)))
        duration_ms = self._duration_ms(result, started[0])
        status = str(getattr(result, "status", "") or "").upper()
        if status not in ROBOT_TO_TEST_RESULT_STATUS:
            status = "SKIP"

        self._results.append(
            RobotTestResult(
                longname=longname,
                name=str(getattr(result, "name", None) or getattr(data, "name", "") or longname),
                suite_name=self._suite_name(longname),
                status=status,
                duration_ms=duration_ms,
                started_ms=started[1],
                message=str(getattr(result, "message", "") or ""),
                external_test_id=self._external_test_id(data),
            )
        )

    def end_suite(self, data: Any, result: Any) -> None:
        if self._is_root_suite(data, result):
            self._submit_results()

    def close(self) -> None:
        self._submit_results()

    def _submit_results(self) -> None:
        if self._submitted:
            return
        self._submitted = True
        if not self._results:
            self._log_warn("No Robot test results collected; nothing sent to Octane")
            return

        xml_payload = build_test_results_xml(self._results, self.options)
        response = self.client.submit_test_results(
            xml_payload,
            skip_errors=self.options.skip_errors,
        )
        task_id = str(response.get("id") or "")
        status = str(response.get("status") or "accepted")
        self._log_info(
            f"Submitted {len(self._results)} Robot test results to Octane "
            f"test-results API; task status={status}, id={task_id or '<none>'}",
            also_console=True,
        )
        if task_id and self.options.wait_seconds > 0:
            final_task = self._wait_for_task(task_id)
            self._log_info(
                "Octane test-results task completed with status="
                f"{final_task.get('status', '<unknown>')}",
                also_console=True,
            )

    def _wait_for_task(self, task_id: str) -> dict[str, Any]:
        deadline = time.monotonic() + self.options.wait_seconds
        last_task: dict[str, Any] = {}
        while time.monotonic() < deadline:
            last_task = self.client.get_test_results_task(task_id)
            status = str(last_task.get("status") or "").upper()
            if status not in {"QUEUED", "RUNNING"}:
                return last_task
            time.sleep(2)
        return last_task

    @staticmethod
    def _duration_ms(result: Any, started_monotonic: float) -> int:
        elapsed = getattr(result, "elapsedtime", None)
        if isinstance(elapsed, (int, float)):
            return int(elapsed)
        elapsed_time = getattr(result, "elapsed_time", None)
        total_seconds = getattr(elapsed_time, "total_seconds", None)
        if callable(total_seconds):
            return int(total_seconds() * 1000)
        return int((time.monotonic() - started_monotonic) * 1000)

    @staticmethod
    def _is_root_suite(data: Any, result: Any) -> bool:
        for source in (data, result):
            parent = getattr(source, "parent", None)
            if parent is not None:
                return False
        return True

    @staticmethod
    def _external_test_id(data: Any) -> str:
        tags = extract_robot_octane_tags(getattr(data, "tags", []))
        return tags[0] if tags else ""

    @staticmethod
    def _suite_name(longname: str) -> str:
        if "." not in longname:
            return "robot"
        return longname.rsplit(".", 1)[0]

    @staticmethod
    def _test_long_name(data: Any, result: Any) -> str:
        for source in (data, result):
            value = getattr(source, "longname", None)
            if value:
                return str(value)
        for source in (data, result):
            value = getattr(source, "name", None)
            if value:
                return str(value)
        return "<unknown>"

    @staticmethod
    def _log_info(message: str, also_console: bool = False) -> None:
        if robot_logger:
            robot_logger.info(message, also_console=also_console)
        else:
            print(message)

    @staticmethod
    def _log_warn(message: str) -> None:
        if robot_logger:
            robot_logger.warn(message)
        else:
            print(f"WARNING: {message}")

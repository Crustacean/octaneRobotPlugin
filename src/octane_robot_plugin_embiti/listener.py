"""Robot Framework listener that syncs tagged test statuses to Octane."""

from __future__ import annotations

from typing import Any

from .config import OctaneConfig
from .mapping import ChildRunRecord, SuiteRunMapping, build_suite_run_mapping
from .octane_client import OctaneClient
from .tags import extract_robot_octane_tags

try:  # pragma: no cover - Robot is not installed in the unit-test environment.
    from robot.api import logger as robot_logger
except Exception:  # pragma: no cover
    robot_logger = None


ROBOT_TO_OCTANE_STATUS = {
    "PASS": "Passed",
    "FAIL": "Failed",
    "SKIP": "Skipped",
}


class OctaneRobotListener:
    """Robot listener API v3 implementation."""

    ROBOT_LISTENER_API_VERSION = 3

    def __init__(
        self,
        suite_run_id: str | None = None,
        client: OctaneClient | None = None,
        config: OctaneConfig | None = None,
    ) -> None:
        self.config = config or OctaneConfig.from_env(suite_run_id=suite_run_id)
        self.client = client or OctaneClient(self.config)
        self.mapping: SuiteRunMapping | None = None
        self._test_to_child_run: dict[str, ChildRunRecord] = {}
        self._updated_child_run_ids: set[str] = set()
        self._matched_tests: list[tuple[str, str, str]] = []
        self._unmatched_robot_tests: list[tuple[str, str]] = []
        self._untagged_count = 0
        self._started = False

    def start_suite(self, data: Any, result: Any) -> None:
        if self._started:
            return
        self._log_info(
            f"Discovering Octane child runs for suite run {self.config.suite_run_id}"
        )
        self.mapping = build_suite_run_mapping(self.client, self.config.suite_run_id)
        self._started = True
        self._log_info(
            "Discovered "
            f"{len(self.mapping.child_runs)} child runs and "
            f"{len(self.mapping.by_normalized_tag)} Octane mapping tags"
        )

    def start_test(self, data: Any, result: Any) -> None:
        self._ensure_mapping()
        test_name = self._test_long_name(data, result)
        robot_tags = extract_robot_octane_tags(getattr(data, "tags", []))
        if not robot_tags:
            self._untagged_count += 1
            return
        if len(robot_tags) > 1:
            self._unmatched_robot_tests.append((test_name, ", ".join(robot_tags)))
            self._log_warn(
                f"Robot test {test_name!r} has multiple octane_tag:* tags: "
                + ", ".join(robot_tags)
                + "; leaving Octane unchanged"
            )
            return

        robot_tag = robot_tags[0]
        record = self.mapping.find(robot_tag) if self.mapping else None
        if not record:
            self._unmatched_robot_tests.append((test_name, robot_tag))
            self._log_warn(
                f"No Octane child run match for Robot test {test_name!r} "
                f"with tag {robot_tag!r}; leaving Octane unchanged"
            )
            return

        self.client.update_run_status(record.child_run_id, "In Progress")
        self._test_to_child_run[test_name] = record
        self._matched_tests.append((test_name, robot_tag, record.child_run_id))
        self._log_info(
            f"Updated Octane child run {record.child_run_id} to In Progress "
            f"for Robot test {test_name!r}"
        )

    def end_test(self, data: Any, result: Any) -> None:
        test_name = self._test_long_name(data, result)
        record = self._test_to_child_run.get(test_name)
        if not record:
            return

        robot_status = str(getattr(result, "status", "") or "").upper()
        octane_status = ROBOT_TO_OCTANE_STATUS.get(robot_status)
        if not octane_status:
            self._log_warn(
                f"Robot test {test_name!r} finished with unsupported status "
                f"{robot_status!r}; leaving child run {record.child_run_id} In Progress"
            )
            return

        message = str(getattr(result, "message", "") or "").strip() or None
        if octane_status == "Passed":
            message = None
        self.client.update_run_status(record.child_run_id, octane_status, message)
        self._updated_child_run_ids.add(record.child_run_id)
        self._log_info(
            f"Updated Octane child run {record.child_run_id} to {octane_status} "
            f"for Robot test {test_name!r}"
        )

    def close(self) -> None:
        if not self.mapping:
            return
        manual_runs = self.mapping.unmatched_child_runs(self._updated_child_run_ids)
        lines = [
            "Octane Robot reconciliation summary:",
            f"- matched Robot tests updated: {len(self._updated_child_run_ids)}",
            f"- Robot tests with no octane_tag: {self._untagged_count}",
            f"- Robot tests with no Octane match: {len(self._unmatched_robot_tests)}",
            f"- Octane child runs left for manual update: {len(manual_runs)}",
        ]
        if self._unmatched_robot_tests:
            lines.append("Unmatched Robot tests:")
            lines.extend(
                f"- {test_name} [{tag}]" for test_name, tag in self._unmatched_robot_tests
            )
        if manual_runs:
            lines.append("Manual Octane child runs:")
            lines.extend(
                f"- {record.child_run_id}: {record.display_name}" for record in manual_runs
            )
        self._log_info("\n".join(lines), also_console=True)

    def _ensure_mapping(self) -> None:
        if self.mapping:
            return
        self.start_suite(None, None)

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

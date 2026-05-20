"""Build Octane test-results XML payloads from Robot test outcomes."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Iterable
from xml.etree import ElementTree


ROBOT_TO_TEST_RESULT_STATUS = {
    "PASS": "Passed",
    "FAIL": "Failed",
    "SKIP": "Skipped",
}


@dataclass(frozen=True)
class TestResultsOptions:
    module: str = "/robot"
    package: str = "robot"
    test_class: str = "RobotFramework"
    release_name: str = ""
    external_report_url: str = ""
    testing_tool_type: str = ""
    framework: str = ""
    skip_errors: bool = True
    wait_seconds: float = 0.0

    @classmethod
    def from_env(cls) -> "TestResultsOptions":
        return cls(
            module=os.getenv("OCTANE_TEST_RESULTS_MODULE", "/robot"),
            package=os.getenv("OCTANE_TEST_RESULTS_PACKAGE", "robot"),
            test_class=os.getenv("OCTANE_TEST_RESULTS_CLASS", "RobotFramework"),
            release_name=os.getenv("OCTANE_TEST_RESULTS_RELEASE_NAME", ""),
            external_report_url=os.getenv("OCTANE_TEST_RESULTS_REPORT_URL", ""),
            testing_tool_type=os.getenv("OCTANE_TESTING_TOOL_TYPE", ""),
            framework=os.getenv("OCTANE_TEST_FRAMEWORK", ""),
            skip_errors=_bool_from_env(os.getenv("OCTANE_TEST_RESULTS_SKIP_ERRORS", "true")),
            wait_seconds=_float_from_env(os.getenv("OCTANE_TEST_RESULTS_WAIT_SECONDS", "0")),
        )


@dataclass(frozen=True)
class RobotTestResult:
    longname: str
    name: str
    suite_name: str
    status: str
    duration_ms: int
    started_ms: int
    message: str = ""
    external_test_id: str = ""

    @property
    def octane_status(self) -> str:
        return ROBOT_TO_TEST_RESULT_STATUS.get(self.status.upper(), "Skipped")


def build_test_results_xml(
    results: Iterable[RobotTestResult],
    options: TestResultsOptions,
) -> str:
    root = ElementTree.Element("test_result")
    if options.release_name:
        ElementTree.SubElement(root, "release", {"name": options.release_name})

    if options.testing_tool_type or options.framework:
        fields = ElementTree.SubElement(root, "test_fields")
        if options.testing_tool_type:
            ElementTree.SubElement(
                fields,
                "test_field",
                {"type": "Testing_Tool_Type", "value": options.testing_tool_type},
            )
        if options.framework:
            ElementTree.SubElement(
                fields,
                "test_field",
                {"type": "Framework", "value": options.framework},
            )

    runs = ElementTree.SubElement(root, "test_runs")
    for result in results:
        attrs = {
            "module": options.module,
            "package": _xml_attr(result.suite_name or options.package),
            "class": options.test_class,
            "name": _xml_attr(result.name),
            "duration": str(max(0, result.duration_ms)),
            "status": result.octane_status,
            "started": str(max(0, result.started_ms)),
        }
        if result.external_test_id:
            attrs["external_test_id"] = _xml_attr(result.external_test_id)
        if options.external_report_url:
            attrs["external_report_url"] = options.external_report_url

        run = ElementTree.SubElement(runs, "test_run", attrs)
        message = result.message.strip()
        if result.octane_status == "Failed" and message:
            error = ElementTree.SubElement(
                run,
                "error",
                {"type": "RobotFrameworkFailure", "message": _xml_attr(message)},
            )
            error.text = message
        if message:
            description = ElementTree.SubElement(run, "description")
            description.text = message

    return _to_xml(root)


def _to_xml(root: ElementTree.Element) -> str:
    ElementTree.indent(root, space="  ")
    body = ElementTree.tostring(root, encoding="unicode", short_empty_elements=True)
    return f'<?xml version="1.0"?>\n{body}\n'


def _xml_attr(value: str) -> str:
    return value.strip()


def _bool_from_env(value: str) -> bool:
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _float_from_env(value: str) -> float:
    try:
        return float(value)
    except ValueError:
        return 0.0

import os
import unittest
from xml.etree import ElementTree

from octane_robot_plugin_embiti.config import OctaneConfig
from octane_robot_plugin_embiti.test_results import (
    RobotTestResult,
    TestResultsOptions,
    build_test_results_xml,
)


class TestResultsXmlTests(unittest.TestCase):
    def test_builds_octane_test_results_xml(self):
        xml_payload = build_test_results_xml(
            [
                RobotTestResult(
                    longname="Suite.Login",
                    name="Login",
                    suite_name="Suite",
                    status="FAIL",
                    duration_ms=1234,
                    started_ms=1716000000000,
                    message="Expected welcome page",
                    external_test_id="LOGIN_001",
                )
            ],
            TestResultsOptions(
                module="/robot",
                package="robot",
                test_class="RobotFramework",
                release_name="_default_",
                external_report_url="https://ci.example.com/report",
            ),
        )

        root = ElementTree.fromstring(xml_payload)
        self.assertEqual(root.tag, "test_result")
        self.assertEqual(root.find("release").attrib["name"], "_default_")
        run = root.find("test_runs/test_run")
        self.assertEqual(run.attrib["module"], "/robot")
        self.assertEqual(run.attrib["package"], "Suite")
        self.assertEqual(run.attrib["class"], "RobotFramework")
        self.assertEqual(run.attrib["name"], "Login")
        self.assertEqual(run.attrib["status"], "Failed")
        self.assertEqual(run.attrib["duration"], "1234")
        self.assertEqual(run.attrib["external_test_id"], "LOGIN_001")
        self.assertEqual(run.find("error").attrib["message"], "Expected welcome page")
        self.assertEqual(run.find("description").text, "Expected welcome page")

    def test_config_can_load_without_suite_run_for_test_results_injection(self):
        old_env = os.environ.copy()
        try:
            os.environ.update(
                {
                    "OCTANE_BASE_URL": "https://octane.example.com",
                    "OCTANE_SHARED_SPACE_ID": "1001",
                    "OCTANE_WORKSPACE_ID": "2002",
                    "OCTANE_CLIENT_ID": "client",
                    "OCTANE_CLIENT_SECRET": "secret",
                }
            )
            os.environ.pop("OCTANE_SUITE_RUN_ID", None)

            config = OctaneConfig.from_env(require_suite_run_id=False)

            self.assertEqual(config.suite_run_id, "")
        finally:
            os.environ.clear()
            os.environ.update(old_env)


if __name__ == "__main__":
    unittest.main()

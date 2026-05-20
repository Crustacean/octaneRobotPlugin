import io
from contextlib import redirect_stdout
import unittest
from xml.etree import ElementTree

from octane_robot_plugin_embiti.config import OctaneConfig
from octane_robot_plugin_embiti.test_results import TestResultsOptions
from octane_robot_plugin_embiti.test_results_listener import OctaneTestResultsListener


class Obj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeTestResultsClient:
    def __init__(self):
        self.submissions = []

    def submit_test_results(self, xml_payload, skip_errors=True):
        self.submissions.append((xml_payload, skip_errors))
        return {"status": "queued", "id": 1001}


def config():
    return OctaneConfig(
        base_url="https://octane.example.com",
        shared_space_id="1001",
        workspace_id="2002",
        client_id="client",
        client_secret="secret",
        suite_run_id="",
    )


class TestResultsListenerTests(unittest.TestCase):
    def test_startup_prints_version_before_client_id(self):
        client = FakeTestResultsClient()
        listener = OctaneTestResultsListener(
            client=client,
            config=config(),
            options=TestResultsOptions(),
        )

        with redirect_stdout(io.StringIO()) as output:
            listener.start_suite(Obj(), Obj())

        text = output.getvalue()
        version_index = text.index("Octane updater version: v1.0.1")
        client_index = text.index("Using Octane client ID: client")
        self.assertLess(version_index, client_index)

    def test_collects_robot_results_and_submits_xml(self):
        client = FakeTestResultsClient()
        listener = OctaneTestResultsListener(
            client=client,
            config=config(),
            options=TestResultsOptions(module="/robot", test_class="RobotFramework"),
        )
        data = Obj(
            longname="Payments.Login",
            name="Login",
            tags=["octane_tag:LOGIN_001"],
        )

        listener.start_test(data, Obj())
        listener.end_test(data, Obj(status="PASS", message="", elapsedtime=250))

        with redirect_stdout(io.StringIO()) as output:
            listener.end_suite(Obj(), Obj())

        self.assertIn("Submitted 1 Robot test results", output.getvalue())
        self.assertEqual(len(client.submissions), 1)
        xml_payload, skip_errors = client.submissions[0]
        self.assertTrue(skip_errors)
        run = ElementTree.fromstring(xml_payload).find("test_runs/test_run")
        self.assertEqual(run.attrib["package"], "Payments")
        self.assertEqual(run.attrib["name"], "Login")
        self.assertEqual(run.attrib["status"], "Passed")
        self.assertEqual(run.attrib["duration"], "250")
        self.assertEqual(run.attrib["external_test_id"], "LOGIN_001")

    def test_close_does_not_submit_twice_after_root_suite_end(self):
        client = FakeTestResultsClient()
        listener = OctaneTestResultsListener(
            client=client,
            config=config(),
            options=TestResultsOptions(),
        )
        data = Obj(longname="Payments.Login", name="Login", tags=[])

        listener.start_test(data, Obj())
        listener.end_test(data, Obj(status="PASS", message="", elapsedtime=250))
        listener.end_suite(Obj(), Obj())
        listener.close()

        self.assertEqual(len(client.submissions), 1)

    def test_child_suite_end_does_not_submit(self):
        client = FakeTestResultsClient()
        listener = OctaneTestResultsListener(
            client=client,
            config=config(),
            options=TestResultsOptions(),
        )
        data = Obj(longname="Payments.Login", name="Login", tags=[])

        listener.start_test(data, Obj())
        listener.end_test(data, Obj(status="PASS", message="", elapsedtime=250))
        listener.end_suite(Obj(parent=Obj()), Obj())

        self.assertEqual(client.submissions, [])


if __name__ == "__main__":
    unittest.main()

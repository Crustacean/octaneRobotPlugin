import io
from contextlib import redirect_stdout
import unittest

from octane_robot_plugin_embiti.config import OctaneConfig
from octane_robot_plugin_embiti.listener import OctaneRobotListener


class Obj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeListenerClient:
    def __init__(self):
        self.updates = []

    def get_suite_child_run_ids(self, suite_run_id):
        return ["10", "11"]

    def get_run(self, run_id, fields=None):
        return {
            "10": {"id": "10", "name": "login child", "test": {"id": "T1"}},
            "11": {"id": "11", "name": "manual child", "test": {"id": "T2"}},
        }[run_id]

    def get_run_test(self, run):
        return {
            "T1": {
                "id": "T1",
                "name": "Login",
                "user_tags": {"data": [{"name": "LOGIN_001"}]},
            },
            "T2": {
                "id": "T2",
                "name": "Manual",
                "user_tags": {"data": [{"name": "MANUAL_001"}]},
            },
        }[run["test"]["id"]]

    def update_run_status(self, child_run_id, status_name, message=None):
        self.updates.append((child_run_id, status_name, message))


def config():
    return OctaneConfig(
        base_url="https://octane.example.com",
        shared_space_id="1001",
        workspace_id="2002",
        client_id="client",
        client_secret="secret",
        suite_run_id="9001",
    )


class ListenerTests(unittest.TestCase):
    def test_matched_test_updates_in_progress_and_final_status(self):
        client = FakeListenerClient()
        listener = OctaneRobotListener(config=config(), client=client)
        data = Obj(longname="Suite.Login", tags=["octane_tag:login_001"])

        listener.start_test(data, Obj())
        listener.end_test(data, Obj(status="PASS", message=""))

        self.assertEqual(
            client.updates,
            [("10", "In Progress", None), ("10", "Passed", None)],
        )

    def test_failed_test_includes_message(self):
        client = FakeListenerClient()
        listener = OctaneRobotListener(config=config(), client=client)
        data = Obj(longname="Suite.Login", tags=["octane_tag:LOGIN_001"])

        listener.start_test(data, Obj())
        listener.end_test(data, Obj(status="FAIL", message="Expected true"))

        self.assertEqual(client.updates[-1], ("10", "Failed", "Expected true"))

    def test_unmatched_robot_tag_warns_and_does_not_update(self):
        client = FakeListenerClient()
        listener = OctaneRobotListener(config=config(), client=client)
        data = Obj(longname="Suite.Unknown", tags=["octane_tag:UNKNOWN"])

        with redirect_stdout(io.StringIO()) as output:
            listener.start_test(data, Obj())
            listener.end_test(data, Obj(status="PASS", message=""))

        self.assertEqual(client.updates, [])
        self.assertIn("No Octane child run match", output.getvalue())

    def test_multiple_robot_mapping_tags_warns_and_does_not_update(self):
        client = FakeListenerClient()
        listener = OctaneRobotListener(config=config(), client=client)
        data = Obj(
            longname="Suite.BadTags",
            tags=["octane_tag:LOGIN_001", "octane_tag:MANUAL_001"],
        )

        with redirect_stdout(io.StringIO()) as output:
            listener.start_test(data, Obj())
            listener.end_test(data, Obj(status="PASS", message=""))

        self.assertEqual(client.updates, [])
        self.assertIn("multiple octane_tag", output.getvalue())

    def test_close_prints_reconciliation_summary(self):
        client = FakeListenerClient()
        listener = OctaneRobotListener(config=config(), client=client)
        data = Obj(longname="Suite.Login", tags=["octane_tag:LOGIN_001"])
        untagged = Obj(longname="Suite.Local", tags=[])

        listener.start_test(data, Obj())
        listener.end_test(data, Obj(status="PASS", message=""))
        listener.start_test(untagged, Obj())

        with redirect_stdout(io.StringIO()) as output:
            listener.close()

        summary = output.getvalue()
        self.assertIn("matched Robot tests updated: 1", summary)
        self.assertIn("Robot tests with no octane_tag: 1", summary)
        self.assertIn("Octane child runs left for manual update: 1", summary)
        self.assertIn("11: Manual / manual child", summary)


if __name__ == "__main__":
    unittest.main()

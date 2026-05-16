import unittest

from octane_robot_plugin_embiti.config import OctaneConfig
from octane_robot_plugin_embiti.octane_client import OctaneClient


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text if text is not None else "{}"

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self.posts = []
        self.requests = []

    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        return FakeResponse(payload={})

    def request(self, method, url, **kwargs):
        self.requests.append((method, url, kwargs))
        if method == "GET" and url.endswith("/runs/10"):
            return FakeResponse(
                payload={
                    "id": "10",
                    "client_lock_stamp": 7,
                    "description": "Existing description",
                }
            )
        if method == "GET" and url.endswith("/list_nodes"):
            return FakeResponse(
                payload={
                    "data": [
                        {
                            "id": "status_failed",
                            "type": "list_node",
                            "name": "Failed",
                            "logical_name": "list_node.run_native_status.failed",
                        }
                    ]
                }
            )
        if method == "PUT" and url.endswith("/runs/10"):
            return FakeResponse(payload={})
        raise AssertionError(f"Unexpected request: {method} {url}")


def config():
    return OctaneConfig(
        base_url="https://octane.example.com",
        shared_space_id="1001",
        workspace_id="2002",
        client_id="client",
        client_secret="secret",
        suite_run_id="9001",
    )


class OctaneClientTests(unittest.TestCase):
    def test_test_subtypes_use_tests_collection_path(self):
        self.assertEqual(OctaneClient._entity_collection_path("test_manual"), "tests")
        self.assertEqual(OctaneClient._entity_collection_path("test_automated"), "tests")
        self.assertEqual(OctaneClient._entity_collection_path("gherkin_test"), "tests")

    def test_update_run_status_uses_lock_stamp_and_resolved_status_node(self):
        session = FakeSession()
        client = OctaneClient(config(), session=session, max_retries=0)

        client.update_run_status("10", "Failed", "Expected true")

        self.assertEqual(session.posts[0][0], "https://octane.example.com/authentication/sign_in")
        put_request = [
            item for item in session.requests if item[0] == "PUT" and item[1].endswith("/runs/10")
        ][0]
        body = put_request[2]["json"]
        self.assertEqual(body["id"], "10")
        self.assertEqual(body["type"], "run")
        self.assertEqual(body["client_lock_stamp"], 7)
        self.assertEqual(body["native_status"], {"type": "list_node", "id": "status_failed"})
        self.assertIn("Expected true", body["description"])

        run_get = [
            item for item in session.requests if item[0] == "GET" and item[1].endswith("/runs/10")
        ][0]
        self.assertNotIn("type", run_get[2]["params"]["fields"].split(","))


if __name__ == "__main__":
    unittest.main()

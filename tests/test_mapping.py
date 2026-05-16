import unittest

from octane_robot_plugin_embiti.errors import DuplicateOctaneTagError
from octane_robot_plugin_embiti.mapping import build_suite_run_mapping


class FakeMappingClient:
    def __init__(self, runs, tests):
        self.runs = runs
        self.tests = tests

    def get_suite_child_run_ids(self, suite_run_id):
        return list(self.runs)

    def get_run(self, run_id, fields=None):
        return self.runs[run_id]

    def get_run_test(self, run):
        return self.tests[run["test"]["id"]]


class MappingTests(unittest.TestCase):
    def test_builds_case_insensitive_mapping_from_octane_user_tags(self):
        client = FakeMappingClient(
            runs={
                "10": {"id": "10", "name": "child login", "test": {"id": "T1"}},
                "11": {"id": "11", "name": "child checkout", "test": {"id": "T2"}},
            },
            tests={
                "T1": {
                    "id": "T1",
                    "name": "Login",
                    "user_tags": {"data": [{"name": "LOGIN_001"}]},
                },
                "T2": {
                    "id": "T2",
                    "name": "Checkout",
                    "user_tags": {"data": [{"name": "CHECKOUT_001"}]},
                },
            },
        )

        mapping = build_suite_run_mapping(client, "9001")

        self.assertEqual(mapping.find("login_001").child_run_id, "10")
        self.assertEqual(mapping.find("CHECKOUT_001").child_run_id, "11")
        self.assertIsNone(mapping.find("unknown"))

    def test_duplicate_octane_user_tag_fails(self):
        client = FakeMappingClient(
            runs={
                "10": {"id": "10", "name": "child 1", "test": {"id": "T1"}},
                "11": {"id": "11", "name": "child 2", "test": {"id": "T2"}},
            },
            tests={
                "T1": {
                    "id": "T1",
                    "name": "Test 1",
                    "user_tags": {"data": [{"name": "DUPLICATE"}]},
                },
                "T2": {
                    "id": "T2",
                    "name": "Test 2",
                    "user_tags": {"data": [{"name": "duplicate"}]},
                },
            },
        )

        with self.assertRaises(DuplicateOctaneTagError):
            build_suite_run_mapping(client, "9001")

    def test_child_run_without_tags_is_left_for_manual_update(self):
        client = FakeMappingClient(
            runs={
                "10": {"id": "10", "name": "child login", "test": {"id": "T1"}},
                "11": {"id": "11", "name": "manual child", "test": {"id": "T2"}},
            },
            tests={
                "T1": {
                    "id": "T1",
                    "name": "Login",
                    "user_tags": {"data": [{"name": "LOGIN_001"}]},
                },
                "T2": {"id": "T2", "name": "Manual", "user_tags": {"data": []}},
            },
        )

        mapping = build_suite_run_mapping(client, "9001")

        self.assertEqual(len(mapping.child_runs), 2)
        self.assertEqual(
            [run.child_run_id for run in mapping.unmatched_child_runs({"10"})],
            ["11"],
        )


if __name__ == "__main__":
    unittest.main()

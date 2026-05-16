import unittest

from octane_robot_plugin_embiti.tags import (
    extract_robot_octane_tags,
    extract_user_tag_names,
    normalize_tag,
)


class TagTests(unittest.TestCase):
    def test_extracts_robot_octane_tag_case_insensitively(self):
        self.assertEqual(
            extract_robot_octane_tags(["smoke", "OCTANE_TAG:Login_001"]),
            ["Login_001"],
        )

    def test_ignores_empty_robot_octane_tag(self):
        self.assertEqual(extract_robot_octane_tags(["octane_tag:"]), [])

    def test_normalize_tag_is_case_insensitive(self):
        self.assertEqual(normalize_tag(" Login_001 "), normalize_tag("login_001"))

    def test_extracts_octane_user_tag_names_from_relationship_payload(self):
        payload = {
            "data": [
                {"type": "user_tag", "id": "1001", "name": "LOGIN_001"},
                {"type": "user_tag", "id": "1002", "name": "Smoke"},
            ]
        }
        self.assertEqual(extract_user_tag_names(payload), ["LOGIN_001", "Smoke"])

    def test_extracts_octane_user_tag_names_from_list_payload(self):
        payload = [{"name": "LOGIN_001"}, "CHECKOUT_001"]
        self.assertEqual(extract_user_tag_names(payload), ["LOGIN_001", "CHECKOUT_001"])


if __name__ == "__main__":
    unittest.main()

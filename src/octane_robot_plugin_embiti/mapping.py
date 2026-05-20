"""Suite-run child run discovery and tag mapping."""

from __future__ import annotations

from dataclasses import dataclass, field

from .errors import DuplicateOctaneTagError
from .tags import extract_user_tag_names, normalize_tag


@dataclass(frozen=True)
class ChildRunRecord:
    child_run_id: str
    child_run_name: str = ""
    run_subtype: str = ""
    test_id: str = ""
    test_name: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_automated_run(self) -> bool:
        return self.run_subtype.strip().lower() in {
            "run_automated",
            "automated_run",
            "test_run",
        }

    @property
    def display_name(self) -> str:
        if self.test_name and self.child_run_name:
            return f"{self.test_name} / {self.child_run_name}"
        return self.test_name or self.child_run_name or self.child_run_id


@dataclass(frozen=True)
class SuiteRunMapping:
    suite_run_id: str
    by_normalized_tag: dict[str, ChildRunRecord]
    child_runs: tuple[ChildRunRecord, ...]

    def find(self, robot_tag: str) -> ChildRunRecord | None:
        return self.by_normalized_tag.get(normalize_tag(robot_tag))

    def unmatched_child_runs(self, updated_child_run_ids: set[str]) -> list[ChildRunRecord]:
        return [
            record
            for record in self.child_runs
            if record.child_run_id not in updated_child_run_ids
        ]


def build_suite_run_mapping(client: object, suite_run_id: str) -> SuiteRunMapping:
    """Build a stable-tag to child-run map for one Octane suite run."""
    child_run_ids = client.get_suite_child_run_ids(suite_run_id)
    records: list[ChildRunRecord] = []
    by_tag: dict[str, ChildRunRecord] = {}

    for child_run_id in child_run_ids:
        child_run = client.get_run(child_run_id)
        test = client.get_run_test(child_run)
        tags = tuple(extract_user_tag_names(test.get("user_tags")))
        record = ChildRunRecord(
            child_run_id=str(child_run.get("id") or child_run_id),
            child_run_name=str(child_run.get("name") or ""),
            run_subtype=str(child_run.get("subtype") or ""),
            test_id=str(test.get("id") or ""),
            test_name=str(test.get("name") or ""),
            tags=tags,
        )
        records.append(record)

        for tag_name in tags:
            normalized = normalize_tag(tag_name)
            existing = by_tag.get(normalized)
            if existing and existing.child_run_id != record.child_run_id:
                raise DuplicateOctaneTagError(
                    "Duplicate Octane tag "
                    f"{tag_name!r} found on child runs "
                    f"{existing.child_run_id} and {record.child_run_id}"
                )
            by_tag[normalized] = record

    return SuiteRunMapping(
        suite_run_id=str(suite_run_id),
        by_normalized_tag=by_tag,
        child_runs=tuple(records),
    )

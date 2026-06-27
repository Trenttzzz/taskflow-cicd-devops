import json
import tempfile
import unittest
from pathlib import Path

from scripts.archive_failure import ArchiveError, archive_failure


class ArchiveFailureTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.archive_dir = self.root / "history"
        self.log_path = self.root / "current-failure.cleaned.log"
        self.status_path = self.root / "status.json"
        self.similar_path = self.root / "similar-failures.json"
        self.log_path.write_text("Coverage 72.8% is below 75%\n", encoding="utf-8")
        self.status_path.write_text(
            json.dumps(
                {
                    "should_analyze": True,
                    "failed_jobs": ["ci"],
                }
            ),
            encoding="utf-8",
        )
        self.similar_path.write_text(
            json.dumps(
                {
                    "top_k": [
                        {
                            "rank": 1,
                            "id": "synthetic-001-coverage-gate",
                            "category": "coverage-gate",
                            "similarity": 0.88,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        self.provenance = {
            "run_id": "123456",
            "run_attempt": "1",
            "commit_sha": "abc123",
            "repository": "owner/taskflow",
            "run_url": "https://github.com/owner/taskflow/actions/runs/123456",
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_creates_provisional_real_failure_entry(self):
        result = archive_failure(
            self.archive_dir,
            self.log_path,
            self.status_path,
            self.similar_path,
            self.provenance,
        )

        metadata = json.loads((self.archive_dir / "metadata.json").read_text(encoding="utf-8"))
        entry = metadata["entries"][0]
        archived_log = self.archive_dir / entry["log_file"]

        self.assertEqual("created", result)
        self.assertEqual("real-123456-attempt-1", entry["id"])
        self.assertEqual("real", entry["source_type"])
        self.assertEqual(["ci"], entry["failed_jobs"])
        self.assertEqual("unclassified", entry["category"])
        self.assertFalse(entry["validated"])
        self.assertTrue(archived_log.exists())
        self.assertEqual(self.log_path.read_text(encoding="utf-8"), archived_log.read_text(encoding="utf-8"))

    def test_deduplicates_same_sanitized_log_across_runs(self):
        self.log_path.write_text(
            "html_url: https://github.com/owner/taskflow/actions/runs/123/jobs/111\n"
            "Coverage 72.8% is below 75%\n",
            encoding="utf-8",
        )
        archive_failure(
            self.archive_dir,
            self.log_path,
            self.status_path,
            self.similar_path,
            self.provenance,
        )
        second_provenance = {**self.provenance, "run_id": "654321"}
        self.log_path.write_text(
            "html_url: https://github.com/owner/taskflow/actions/runs/654/jobs/222\n"
            "Coverage 72.8% is below 75%\n",
            encoding="utf-8",
        )

        result = archive_failure(
            self.archive_dir,
            self.log_path,
            self.status_path,
            self.similar_path,
            second_provenance,
        )

        metadata = json.loads((self.archive_dir / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual("duplicate", result)
        self.assertEqual(1, len(metadata["entries"]))

    def test_masks_secret_before_hashing_and_writing(self):
        google_api_key = "AIza" + ("A" * 25)
        self.log_path.write_text(
            f"request failed with token=visible-secret and {google_api_key}\n",
            encoding="utf-8",
        )

        archive_failure(
            self.archive_dir,
            self.log_path,
            self.status_path,
            self.similar_path,
            self.provenance,
        )

        metadata = json.loads((self.archive_dir / "metadata.json").read_text(encoding="utf-8"))
        archived_log = (self.archive_dir / metadata["entries"][0]["log_file"]).read_text(encoding="utf-8")
        self.assertNotIn("visible-secret", archived_log)
        self.assertNotIn(google_api_key, archived_log)
        self.assertIn("[MASKED]", archived_log)

    def test_rejects_success_status(self):
        self.status_path.write_text(
            json.dumps({"should_analyze": False, "failed_jobs": []}),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ArchiveError, "failure"):
            archive_failure(
                self.archive_dir,
                self.log_path,
                self.status_path,
                self.similar_path,
                self.provenance,
            )

    def test_rejects_invalid_status_structure(self):
        self.status_path.write_text(json.dumps(["failure"]), encoding="utf-8")

        with self.assertRaisesRegex(ArchiveError, "Status"):
            archive_failure(
                self.archive_dir,
                self.log_path,
                self.status_path,
                self.similar_path,
                self.provenance,
            )

    def test_does_not_overwrite_corrupt_metadata(self):
        self.archive_dir.mkdir(parents=True)
        metadata_path = self.archive_dir / "metadata.json"
        metadata_path.write_text("{invalid", encoding="utf-8")

        with self.assertRaisesRegex(ArchiveError, "metadata"):
            archive_failure(
                self.archive_dir,
                self.log_path,
                self.status_path,
                self.similar_path,
                self.provenance,
            )

        self.assertEqual("{invalid", metadata_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

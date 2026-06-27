import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_embedding_index import load_validated_history_entries


class BuildEmbeddingIndexHistoryTest(unittest.TestCase):
    def test_loads_only_complete_validated_real_entries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            history_dir = Path(temp_dir)
            (history_dir / "real-logs").mkdir()
            (history_dir / "notes").mkdir()
            (history_dir / "real-logs/validated.log").write_text("validated failure\n", encoding="utf-8")
            (history_dir / "notes/validated.md").write_text("# Validated failure\n", encoding="utf-8")
            metadata = {
                "version": 1,
                "entries": [
                    {
                        "id": "real-validated",
                        "source_type": "real",
                        "category": "coverage-gate",
                        "log_file": "real-logs/validated.log",
                        "note_file": "notes/validated.md",
                        "validated": True,
                        "root_cause": "Coverage di bawah threshold.",
                        "resolution": "Tambahkan test.",
                    },
                    {
                        "id": "real-provisional",
                        "source_type": "real",
                        "category": "unclassified",
                        "log_file": "real-logs/provisional.log",
                        "note_file": "notes/provisional.md",
                        "validated": False,
                        "root_cause": "Menunggu validasi.",
                        "resolution": "Menunggu validasi.",
                    },
                    {
                        "id": "real-missing-files",
                        "source_type": "real",
                        "category": "docker-build",
                        "log_file": "real-logs/missing.log",
                        "note_file": "notes/missing.md",
                        "validated": True,
                        "root_cause": "Docker build gagal.",
                        "resolution": "Perbaiki Dockerfile.",
                    },
                ],
            }
            (history_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

            entries = load_validated_history_entries(history_dir)

            self.assertEqual(["real-validated"], [entry["id"] for entry, _ in entries])
            self.assertEqual(history_dir, entries[0][1])


if __name__ == "__main__":
    unittest.main()

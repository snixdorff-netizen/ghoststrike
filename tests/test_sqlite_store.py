import tempfile
import unittest
from pathlib import Path

from ada_iq.orchestrator import Orchestrator
from ada_iq.store import SQLiteContextStore


class SQLiteStoreTests(unittest.TestCase):
    def test_project_persists_across_store_instances(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "ada_iq.db"
            orchestrator = Orchestrator(store=SQLiteContextStore(db_path))
            project = orchestrator.create_project(
                name="Persistent project",
                brief="Verify state survives creation of a new store instance.",
            )
            orchestrator.start_current_phase(project.project_id)

            reloaded_orchestrator = Orchestrator(store=SQLiteContextStore(db_path))
            snapshot = reloaded_orchestrator.get_project_snapshot(project.project_id)

            self.assertEqual(snapshot["project"]["name"], "Persistent project")
            self.assertEqual(snapshot["project"]["status"], "WAITING_FOR_GATE")
            self.assertEqual(len(snapshot["outputs"]), 3)
            self.assertEqual(len(snapshot["messages"]), 7)


if __name__ == "__main__":
    unittest.main()

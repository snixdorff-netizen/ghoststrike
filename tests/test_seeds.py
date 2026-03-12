import tempfile
import unittest
from pathlib import Path

from ada_iq.orchestrator import Orchestrator
from ada_iq.seeds import seed_demo_projects
from ada_iq.store import SQLiteContextStore


class SeedTests(unittest.TestCase):
    def test_seed_demo_projects_populates_empty_store_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "ada_iq.db"
            store = SQLiteContextStore(db_path)
            orchestrator = Orchestrator(store=store)

            created = seed_demo_projects(orchestrator, Path("src/ada_iq/data/demo_projects.json"))
            self.assertEqual(created, 3)
            self.assertEqual(len(orchestrator.list_projects_snapshot()), 3)

            created_again = seed_demo_projects(orchestrator, Path("src/ada_iq/data/demo_projects.json"))
            self.assertEqual(created_again, 0)
            self.assertEqual(len(orchestrator.list_projects_snapshot()), 3)


if __name__ == "__main__":
    unittest.main()

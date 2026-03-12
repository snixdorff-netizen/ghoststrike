import unittest

from ada_iq.orchestrator import Orchestrator
from ada_iq.store import InMemoryContextStore


class ExecutionRunTests(unittest.TestCase):
    def test_phase_start_creates_completed_run_record(self) -> None:
        store = InMemoryContextStore()
        orchestrator = Orchestrator(store=store)
        project = orchestrator.create_project(
            name="Run Tracking",
            brief="Verify that phase execution creates a persistent run record.",
        )

        orchestrator.start_current_phase(project.project_id)
        runs = store.list_runs(project.project_id)

        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0].status.value, "COMPLETED")
        self.assertIn("opened a human gate", runs[0].summary)

    def test_export_snapshot_contains_partner_review_notes(self) -> None:
        store = InMemoryContextStore()
        orchestrator = Orchestrator(store=store)
        project = orchestrator.create_project(
            name="Export Check",
            brief="Verify partner export output includes review metadata.",
        )

        export = orchestrator.export_project_snapshot(project.project_id)
        self.assertEqual(export["export_version"], "1.0")
        self.assertTrue(export["partner_review_notes"])


if __name__ == "__main__":
    unittest.main()

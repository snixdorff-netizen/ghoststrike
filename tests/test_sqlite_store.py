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

    def test_smart_brief_and_compliance_persist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "ada_iq.db"
            orchestrator = Orchestrator(store=SQLiteContextStore(db_path))
            project = orchestrator.create_project(
                name="Persistent smart brief",
                brief="",
                tenant_id="tenant-preview",
                smart_brief={
                    "category": "Kitchen appliance",
                    "price_point": "$249",
                    "consumer_profile": "Time-constrained home cooks",
                    "geo_market": "North America",
                    "competitive_set": ["Ninja", "Instant"],
                    "brand_guardrails": "Premium simplicity",
                    "constraints": "Holiday line review deadline",
                    "launch_season": "Holiday 2027",
                    "uploaded_docs": ["research_pack.pdf"],
                    "open_context": "Need a brief that aligns product and merchandising.",
                },
            )

            reloaded_orchestrator = Orchestrator(store=SQLiteContextStore(db_path))
            snapshot = reloaded_orchestrator.get_project_snapshot(project.project_id)

            self.assertEqual(snapshot["project"]["tenant_id"], "tenant-preview")
            self.assertEqual(snapshot["project"]["smart_brief"]["price_point"], "$249")
            self.assertEqual(snapshot["project"]["compliance"]["data_classification"], "CONFIDENTIAL")

    def test_outputs_jobs_and_events_inherit_governance_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "ada_iq.db"
            orchestrator = Orchestrator(store=SQLiteContextStore(db_path))
            project = orchestrator.create_project(
                name="Governed package",
                brief="",
                tenant_id="tenant-governed",
                smart_brief={
                    "category": "Trail running footwear",
                    "price_point": "$165",
                    "consumer_profile": "Experienced trail runners",
                    "geo_market": "United States",
                    "competitive_set": ["Hoka Speedgoat"],
                    "brand_guardrails": "Premium performance",
                    "constraints": "Spring review cycle",
                    "launch_season": "Spring 2027",
                    "uploaded_docs": ["signal_pack.pdf"],
                    "open_context": "Need a stronger market-entry brief.",
                },
            )
            queued_project = orchestrator.create_project(
                name="Governed queue",
                brief="Queue governance test.",
                tenant_id="tenant-governed",
            )
            orchestrator.start_current_phase(project.project_id)
            job = orchestrator.enqueue_current_phase(queued_project.project_id)

            reloaded_orchestrator = Orchestrator(store=SQLiteContextStore(db_path))
            snapshot = reloaded_orchestrator.get_project_snapshot(project.project_id)

            self.assertTrue(all(output["tenant_id"] == "tenant-governed" for output in snapshot["outputs"]))
            self.assertTrue(all(output["data_classification"] == "CONFIDENTIAL" for output in snapshot["outputs"]))
            self.assertEqual(snapshot["events"][0]["tenant_id"], "tenant-governed")
            self.assertEqual(job["tenant_id"], "tenant-governed")


if __name__ == "__main__":
    unittest.main()

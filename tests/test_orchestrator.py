import unittest

from ada_iq.models import DFNPhase, GateStatus, ProjectStatus
from ada_iq.orchestrator import Orchestrator
from ada_iq.store import InMemoryContextStore


class OrchestratorTests(unittest.TestCase):
    def test_project_advances_through_phase_gate(self) -> None:
        orchestrator = Orchestrator(store=InMemoryContextStore())
        project = orchestrator.create_project(
            name="Cole Haan pilot",
            brief="Build a launchable multi-agent workflow for physical product development.",
        )

        project = orchestrator.start_current_phase(project.project_id)
        self.assertEqual(project.current_phase, DFNPhase.EMPATHIZE)
        self.assertEqual(project.status, ProjectStatus.WAITING_FOR_GATE)
        self.assertEqual(project.gate.status, GateStatus.PENDING)

        project = orchestrator.submit_decision(project.project_id, approved=True, feedback="Proceed")
        self.assertEqual(project.current_phase, DFNPhase.IDEATE)
        self.assertEqual(project.status, ProjectStatus.DRAFT)
        self.assertEqual(project.gate.status, GateStatus.NOT_OPEN)

    def test_project_marks_failed_on_gate_rejection(self) -> None:
        orchestrator = Orchestrator(store=InMemoryContextStore())
        project = orchestrator.create_project(
            name="Rejected pilot",
            brief="Test rejection handling in the human gate workflow.",
        )

        orchestrator.start_current_phase(project.project_id)
        project = orchestrator.submit_decision(project.project_id, approved=False, feedback="Needs revision")
        self.assertEqual(project.status, ProjectStatus.FAILED)

    def test_outputs_are_recorded_for_each_agent_in_phase(self) -> None:
        store = InMemoryContextStore()
        orchestrator = Orchestrator(store=store)
        project = orchestrator.create_project(
            name="Output capture",
            brief="Verify the orchestrator stores specialist outputs for the current phase.",
        )

        orchestrator.start_current_phase(project.project_id)
        outputs = store.list_outputs(project.project_id)
        self.assertEqual(len(outputs), 3)
        self.assertEqual({output.agent_id for output in outputs}, {"agent-1", "agent-2", "agent-3"})

    def test_structured_smart_brief_is_stored_on_project(self) -> None:
        orchestrator = Orchestrator(store=InMemoryContextStore())
        project = orchestrator.create_project(
            name="Smart brief test",
            brief="",
            tenant_id="tenant-acme",
            smart_brief={
                "category": "Trail running footwear",
                "price_point": "$165",
                "consumer_profile": "Experienced trail runners",
                "geo_market": "United States",
                "competitive_set": ["Hoka Speedgoat", "Salomon Genesis"],
                "brand_guardrails": "Premium but approachable",
                "constraints": "Stay in premium margin targets",
                "launch_season": "Spring 2027",
                "uploaded_docs": ["signal_pack.pdf"],
                "open_context": "Need a stronger market-entry brief.",
            },
        )

        snapshot = orchestrator.get_project_snapshot(project.project_id)
        self.assertEqual(snapshot["project"]["tenant_id"], "tenant-acme")
        self.assertEqual(snapshot["project"]["compliance"]["status"], "TRACKED")
        self.assertEqual(snapshot["project"]["smart_brief"]["category"], "Trail running footwear")
        self.assertEqual(len(snapshot["project"]["smart_brief"]["modules"]), 9)

    def test_export_includes_smart_brief_snapshot(self) -> None:
        orchestrator = Orchestrator(store=InMemoryContextStore())
        project = orchestrator.create_project(
            name="Export smart brief",
            brief="",
            smart_brief={
                "category": "Trail running footwear",
                "price_point": "$165",
                "consumer_profile": "Experienced trail runners",
                "geo_market": "United States",
                "competitive_set": ["Hoka Speedgoat"],
                "brand_guardrails": "Premium but approachable",
                "constraints": "Stay in premium margin targets",
                "launch_season": "Spring 2027",
                "uploaded_docs": ["signal_pack.pdf"],
                "open_context": "Need a stronger market-entry brief.",
            },
        )

        exported = orchestrator.export_project_snapshot(project.project_id)
        self.assertEqual(exported["smart_brief_export"]["project_name"], "Export smart brief")
        self.assertEqual(len(exported["smart_brief_export"]["modules"]), 9)
        self.assertIn("Experienced trail runners", exported["smart_brief_export"]["summary"])

    def test_dedicated_smart_brief_package_includes_supporting_outputs(self) -> None:
        orchestrator = Orchestrator(store=InMemoryContextStore())
        project = orchestrator.create_project(
            name="Dedicated smart brief package",
            brief="",
            smart_brief={
                "category": "Trail running footwear",
                "price_point": "$165",
                "consumer_profile": "Experienced trail runners",
                "geo_market": "United States",
                "competitive_set": ["Hoka Speedgoat"],
                "brand_guardrails": "Premium but approachable",
                "constraints": "Stay in premium margin targets",
                "launch_season": "Spring 2027",
                "uploaded_docs": ["signal_pack.pdf"],
                "open_context": "Need a stronger market-entry brief.",
            },
        )

        orchestrator.start_current_phase(project.project_id)
        exported = orchestrator.get_smart_brief_package(project.project_id)

        self.assertEqual(exported["package_type"], "smart_product_brief")
        self.assertEqual(exported["input"]["category"], "Trail running footwear")
        self.assertEqual(len(exported["modules"]), 9)
        self.assertEqual(len(exported["supporting_outputs"]), 2)
        consumer_module = next(module for module in exported["modules"] if module["key"] == "consumer_insight")
        self.assertTrue(consumer_module["citations"])
        self.assertGreaterEqual(consumer_module["version"], 2)
        self.assertTrue(consumer_module["revisions"])

    def test_smart_brief_module_update_versions_content(self) -> None:
        orchestrator = Orchestrator(store=InMemoryContextStore())
        project = orchestrator.create_project(
            name="Editable smart brief",
            brief="",
            owner_user_id="system",
            smart_brief={
                "category": "Trail running footwear",
                "price_point": "$165",
                "consumer_profile": "Experienced trail runners",
                "geo_market": "United States",
                "competitive_set": ["Hoka Speedgoat"],
                "brand_guardrails": "Premium but approachable",
                "constraints": "Stay in premium margin targets",
                "launch_season": "Spring 2027",
                "uploaded_docs": ["signal_pack.pdf"],
                "open_context": "Need a stronger market-entry brief.",
            },
        )

        package_before = orchestrator.get_smart_brief_package(project.project_id)
        updated = orchestrator.update_smart_brief_module(
            project.project_id,
            "executive_summary",
            "Updated executive summary for investor review.",
            owner_user_id="system",
        )

        before_module = next(module for module in package_before["modules"] if module["key"] == "executive_summary")
        after_module = next(module for module in updated["modules"] if module["key"] == "executive_summary")
        self.assertEqual(after_module["content"], "Updated executive summary for investor review.")
        self.assertEqual(after_module["version"], before_module["version"] + 1)
        self.assertEqual(len(after_module["revisions"]), 1)


if __name__ == "__main__":
    unittest.main()

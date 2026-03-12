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


if __name__ == "__main__":
    unittest.main()

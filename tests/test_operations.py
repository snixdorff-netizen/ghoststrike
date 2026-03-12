import unittest

from ada_iq.orchestrator import Orchestrator
from ada_iq.store import InMemoryContextStore


class OperationsTests(unittest.TestCase):
    def test_queue_and_process_job_updates_project_and_job_state(self) -> None:
        orchestrator = Orchestrator(store=InMemoryContextStore())
        project = orchestrator.create_project(
            name="Queued Project",
            brief="Launch an AI-native footwear concept targeting urban professionals in the United States.",
        )

        job = orchestrator.enqueue_current_phase(project.project_id)
        self.assertEqual(job["status"], "QUEUED")

        processed = orchestrator.process_job(job["job_id"])
        self.assertEqual(processed["status"], "COMPLETED")

        snapshot = orchestrator.get_project_snapshot(project.project_id)
        self.assertEqual(snapshot["project"]["status"], "WAITING_FOR_GATE")
        self.assertTrue(snapshot["jobs"])
        self.assertTrue(snapshot["events"])

    def test_event_log_records_phase_transitions(self) -> None:
        orchestrator = Orchestrator(store=InMemoryContextStore())
        project = orchestrator.create_project(
            name="Eventful Project",
            brief="Assess a premium kitchen appliance for busy households with safety and ergonomic design.",
        )

        orchestrator.start_current_phase(project.project_id)
        events = orchestrator.get_project_snapshot(project.project_id)["events"]
        event_types = {event["event_type"] for event in events}

        self.assertIn("phase_started", event_types)
        self.assertIn("phase_completed", event_types)

    def test_queued_job_preserves_requesting_actor(self) -> None:
        orchestrator = Orchestrator(store=InMemoryContextStore())
        owner = orchestrator.register_user("owner@example.com", "password123")["user"]
        project = orchestrator.create_project(
            name="Queued Audit Project",
            brief="Build an audit trail for queued workflow execution.",
            owner_user_id=owner["user_id"],
        )

        job = orchestrator.enqueue_current_phase(project.project_id, owner["user_id"])
        processed = orchestrator.process_job(job["job_id"])
        snapshot = orchestrator.get_project_snapshot(project.project_id, owner["user_id"])

        self.assertEqual(processed["status"], "COMPLETED")
        self.assertEqual(snapshot["jobs"][0]["requested_by"], "owner@example.com")
        self.assertEqual(snapshot["runs"][0]["triggered_by"], "owner@example.com")
        actors = {event["data"].get("actor") for event in snapshot["events"]}
        self.assertIn("owner@example.com", actors)


if __name__ == "__main__":
    unittest.main()

import unittest

from ada_iq.orchestrator import Orchestrator
from ada_iq.store import InMemoryContextStore


class CollaborationTests(unittest.TestCase):
    def test_owner_can_add_collaborator_and_collaborator_can_read(self) -> None:
        orchestrator = Orchestrator(store=InMemoryContextStore())
        owner = orchestrator.register_user("owner@example.com", "password123")["user"]
        viewer = orchestrator.register_user("viewer@example.com", "password123")["user"]
        project = orchestrator.create_project(name="Shared Project", brief="Shareable brief.", owner_user_id=owner["user_id"])

        orchestrator.add_project_collaborator(project.project_id, owner["user_id"], "viewer@example.com", "VIEWER")
        snapshot = orchestrator.get_project_snapshot(project.project_id, viewer["user_id"])

        self.assertEqual(snapshot["project"]["name"], "Shared Project")
        self.assertEqual(snapshot["collaborators"][0]["access_role"], "VIEWER")
        visible_projects = orchestrator.list_projects_snapshot(viewer["user_id"])
        self.assertEqual(visible_projects[0]["project_id"], project.project_id)

    def test_viewer_cannot_run_phase_but_editor_can(self) -> None:
        orchestrator = Orchestrator(store=InMemoryContextStore())
        owner = orchestrator.register_user("owner@example.com", "password123")["user"]
        viewer = orchestrator.register_user("viewer@example.com", "password123")["user"]
        editor = orchestrator.register_user("editor@example.com", "password123")["user"]
        project = orchestrator.create_project(name="Shared Project", brief="Shareable brief.", owner_user_id=owner["user_id"])

        orchestrator.add_project_collaborator(project.project_id, owner["user_id"], "viewer@example.com", "VIEWER")
        orchestrator.add_project_collaborator(project.project_id, owner["user_id"], "editor@example.com", "EDITOR")

        with self.assertRaises(PermissionError):
            orchestrator.start_current_phase(project.project_id, owner_user_id=viewer["user_id"])

        project = orchestrator.start_current_phase(project.project_id, owner_user_id=editor["user_id"])
        self.assertEqual(project.status.value, "WAITING_FOR_GATE")

    def test_invitation_acceptance_creates_collaborator(self) -> None:
        orchestrator = Orchestrator(store=InMemoryContextStore())
        owner = orchestrator.register_user("owner@example.com", "password123")["user"]
        invited = orchestrator.register_user("invitee@example.com", "password123")["user"]
        project = orchestrator.create_project(name="Invited Project", brief="Shareable brief.", owner_user_id=owner["user_id"])

        invitation = orchestrator.invite_project_collaborator(project.project_id, owner["user_id"], "invitee@example.com", "EDITOR")
        collaborator = orchestrator.accept_invitation(invitation["token"], invited["user_id"])
        snapshot = orchestrator.get_project_snapshot(project.project_id, invited["user_id"])

        self.assertEqual(collaborator["access_role"], "EDITOR")
        self.assertEqual(snapshot["collaborators"][0]["user_id"], invited["user_id"])
        event_types = [event["event_type"] for event in snapshot["events"]]
        self.assertIn("invitation_created", event_types)
        self.assertIn("invitation_accepted", event_types)


if __name__ == "__main__":
    unittest.main()

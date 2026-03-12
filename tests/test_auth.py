import unittest

from ada_iq.orchestrator import Orchestrator
from ada_iq.store import InMemoryContextStore


class AuthTests(unittest.TestCase):
    def test_register_and_login_create_session_and_user(self) -> None:
        orchestrator = Orchestrator(store=InMemoryContextStore())

        registration = orchestrator.register_user("user@example.com", "password123")
        self.assertEqual(registration["user"]["email"], "user@example.com")
        self.assertEqual(registration["user"]["role"], "MEMBER")
        self.assertTrue(registration["token"])

        login = orchestrator.login_user("user@example.com", "password123")
        self.assertEqual(login["user"]["email"], "user@example.com")
        self.assertTrue(login["token"])

    def test_project_access_is_scoped_to_owner(self) -> None:
        orchestrator = Orchestrator(store=InMemoryContextStore())
        owner = orchestrator.register_user("owner@example.com", "password123")["user"]
        other = orchestrator.register_user("other@example.com", "password123")["user"]

        project = orchestrator.create_project(name="Private Project", brief="Scoped project.", owner_user_id=owner["user_id"])
        snapshot = orchestrator.get_project_snapshot(project.project_id, owner["user_id"])
        self.assertEqual(snapshot["project"]["name"], "Private Project")

        with self.assertRaises(PermissionError):
            orchestrator.get_project_snapshot(project.project_id, other["user_id"])

    def test_admin_can_list_users_and_projects(self) -> None:
        orchestrator = Orchestrator(store=InMemoryContextStore())
        admin = orchestrator.register_user("admin@example.com", "password123", role="ADMIN")["user"]
        member = orchestrator.register_user("member@example.com", "password123")["user"]
        orchestrator.create_project(name="Admin Viewable", brief="Shared admin listing.", owner_user_id=member["user_id"])

        users = orchestrator.list_users(admin["user_id"])
        projects = orchestrator.list_all_projects(admin["user_id"])

        self.assertEqual(len(users), 2)
        self.assertEqual(len(projects), 1)

        with self.assertRaises(PermissionError):
            orchestrator.list_users(member["user_id"])


if __name__ == "__main__":
    unittest.main()

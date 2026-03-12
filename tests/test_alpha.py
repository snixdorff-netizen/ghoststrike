import unittest
from pathlib import Path

import ada_iq.api as api_module
from ada_iq.config import Settings
from ada_iq.orchestrator import Orchestrator
from ada_iq.seeds import ensure_admin_user, seed_demo_projects
from ada_iq.store import InMemoryContextStore


class AlphaControlsTests(unittest.TestCase):
    def test_admin_can_create_alpha_user(self) -> None:
        orchestrator = Orchestrator(store=InMemoryContextStore())
        admin = orchestrator.register_user("admin@example.com", "password123", role="ADMIN")["user"]

        created = orchestrator.admin_create_user(admin["user_id"], "alpha@example.com", "password123", "MEMBER")

        self.assertEqual(created["user"]["email"], "alpha@example.com")
        self.assertEqual(created["user"]["role"], "MEMBER")
        users = orchestrator.list_users(admin["user_id"])
        self.assertEqual(len(users), 2)

    def test_project_feedback_is_persisted_and_listed(self) -> None:
        orchestrator = Orchestrator(store=InMemoryContextStore())
        owner = orchestrator.register_user("owner@example.com", "password123")["user"]
        project = orchestrator.create_project(name="Feedback Project", brief="Capture alpha feedback.", owner_user_id=owner["user_id"])

        submitted = orchestrator.submit_project_feedback(project.project_id, owner["user_id"], "The invitation flow was clear.", "UX")
        listed = orchestrator.list_project_feedback(project.project_id, owner["user_id"])
        snapshot = orchestrator.get_project_snapshot(project.project_id, owner["user_id"])

        self.assertEqual(submitted["event_type"], "alpha_feedback")
        self.assertEqual(listed[0]["message"], "The invitation flow was clear.")
        self.assertEqual(snapshot["feedback"][0]["data"]["category"], "UX")

    def test_closed_registration_blocks_public_signup(self) -> None:
        original_settings = api_module.settings
        original_orchestrator = api_module.orchestrator
        try:
            api_module.settings = Settings(
                database_path=Path("/tmp/unused-alpha-test.db"),
                seed_data_path=Path("src/ada_iq/data/demo_projects.json"),
                auto_seed_demo=False,
                open_registration=False,
                bootstrap_admin_email=None,
                bootstrap_admin_password=None,
                build_label="Test Build",
                demo_account_enabled=False,
                demo_account_email="demo@adaiq.local",
                demo_account_password="demo12345",
            )
            api_module.orchestrator = Orchestrator(store=InMemoryContextStore())
            with self.assertRaises(api_module.HTTPException) as context:
                api_module.register(api_module.AuthRequest(email="blocked@example.com", password="password123"))
            self.assertEqual(context.exception.status_code, 403)
        finally:
            api_module.settings = original_settings
            api_module.orchestrator = original_orchestrator

    def test_ensure_admin_user_is_idempotent(self) -> None:
        orchestrator = Orchestrator(store=InMemoryContextStore())

        first = ensure_admin_user(orchestrator, "founder@example.com", "password123")
        second = ensure_admin_user(orchestrator, "founder@example.com", "password123")

        self.assertEqual(first["user"]["email"], "founder@example.com")
        self.assertEqual(second["user"]["role"], "ADMIN")
        self.assertEqual(len(orchestrator.list_users(first["user"]["user_id"])), 1)

    def test_seed_demo_projects_can_use_bootstrap_admin(self) -> None:
        orchestrator = Orchestrator(store=InMemoryContextStore())

        created = seed_demo_projects(
            orchestrator,
            Path("src/ada_iq/data/demo_projects.json"),
            owner_email="founder@example.com",
            owner_password="password123",
        )

        owner = orchestrator.login_user("founder@example.com", "password123")["user"]
        projects = orchestrator.list_projects_snapshot(owner["user_id"])

        self.assertGreater(created, 0)
        self.assertTrue(projects)
        self.assertTrue(all(project["owner_user_id"] == owner["user_id"] for project in projects))

    def test_admin_dashboard_summarizes_activity(self) -> None:
        orchestrator = Orchestrator(store=InMemoryContextStore())
        admin = orchestrator.register_user("admin@example.com", "password123", role="ADMIN")["user"]
        member = orchestrator.register_user("member@example.com", "password123")["user"]
        project = orchestrator.create_project(name="Dashboard Project", brief="Track alpha health.", owner_user_id=member["user_id"])
        orchestrator.start_current_phase(project.project_id, owner_user_id=member["user_id"])
        orchestrator.submit_project_feedback(project.project_id, member["user_id"], "The output quality was strong.", "OUTPUT_QUALITY")

        dashboard = orchestrator.get_admin_dashboard(admin["user_id"])

        self.assertEqual(dashboard["user_count"], 2)
        self.assertEqual(dashboard["project_count"], 1)
        self.assertEqual(dashboard["active_gates"], 1)
        self.assertEqual(dashboard["feedback_count"], 1)
        self.assertEqual(dashboard["feedback_by_category"]["OUTPUT_QUALITY"], 1)
        self.assertTrue(dashboard["latest_activity"])


if __name__ == "__main__":
    unittest.main()

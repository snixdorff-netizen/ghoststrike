import unittest

from ada_iq.agents import list_agent_specs
from ada_iq.orchestrator import Orchestrator
from ada_iq.store import InMemoryContextStore


class MetadataTests(unittest.TestCase):
    def test_agent_specs_cover_all_specialists(self) -> None:
        specs = list_agent_specs()
        self.assertEqual(len(specs), 12)
        self.assertEqual(specs[0]["code_name"], "Ada Scout")

    def test_list_projects_snapshot_returns_api_safe_values(self) -> None:
        orchestrator = Orchestrator(store=InMemoryContextStore())
        orchestrator.create_project(
            name="Snapshot test",
            brief="Ensure project listings serialize into plain API-safe data.",
        )

        snapshot = orchestrator.list_projects_snapshot()
        self.assertEqual(snapshot[0]["current_phase"], "EMPATHIZE")
        self.assertEqual(snapshot[0]["status"], "DRAFT")


if __name__ == "__main__":
    unittest.main()

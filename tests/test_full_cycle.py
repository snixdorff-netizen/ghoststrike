import unittest

from ada_iq.orchestrator import Orchestrator
from ada_iq.store import InMemoryContextStore


class FullCycleTests(unittest.TestCase):
    def test_complete_full_cycle_runs_through_measure_and_completes(self) -> None:
        orchestrator = Orchestrator(store=InMemoryContextStore())
        project = orchestrator.create_project(
            name="Cole Haan Pilot",
            brief=(
                "Launch an AI-native footwear concept targeting urban professionals who want "
                "adaptable comfort and premium direct-to-consumer positioning in the United States."
            ),
        )

        package = orchestrator.complete_full_cycle(project.project_id)

        self.assertEqual(package["workflow"], "full_dfn_cycle")
        self.assertEqual(package["current_phase"], "MEASURE")
        self.assertEqual(package["status"], "COMPLETED")
        output_types = {output["output_type"] for output in package["included_outputs"]}
        self.assertIn("risk_report", output_types)
        self.assertIn("expansion_report", output_types)
        self.assertIn("synthesis_report", output_types)


if __name__ == "__main__":
    unittest.main()

import unittest

from ada_iq.orchestrator import Orchestrator
from ada_iq.store import InMemoryContextStore


class FirstSevenStepsTests(unittest.TestCase):
    def test_complete_first_seven_steps_runs_empathize_and_ideate_bundle(self) -> None:
        orchestrator = Orchestrator(store=InMemoryContextStore())
        project = orchestrator.create_project(
            name="Cole Haan Pilot",
            brief=(
                "Launch an AI-native footwear concept targeting urban professionals who want "
                "adaptable comfort and premium direct-to-consumer positioning in the United States."
            ),
        )

        package = orchestrator.complete_first_seven_steps(project.project_id)

        self.assertEqual(package["workflow"], "first_seven_steps")
        self.assertEqual(package["current_phase"], "IDEATE")
        self.assertEqual(package["status"], "WAITING_FOR_GATE")
        self.assertEqual(len(package["outputs"]), 5)
        self.assertEqual(
            {output["output_type"] for output in package["outputs"]},
            {
                "market_intelligence_report",
                "consumer_insights_report",
                "empathize_report",
                "strategy_report",
                "concept_generation_report",
            },
        )


if __name__ == "__main__":
    unittest.main()

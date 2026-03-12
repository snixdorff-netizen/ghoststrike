import unittest

from ada_iq.orchestrator import Orchestrator
from ada_iq.store import InMemoryContextStore


class V1WorkflowTests(unittest.TestCase):
    def test_complete_v1_workflow_runs_through_realize(self) -> None:
        orchestrator = Orchestrator(store=InMemoryContextStore())
        project = orchestrator.create_project(
            name="Cole Haan Pilot",
            brief=(
                "Launch an AI-native footwear concept targeting urban professionals who want "
                "adaptable comfort and premium direct-to-consumer positioning in the United States."
            ),
        )

        package = orchestrator.complete_v1_workflow(project.project_id)

        self.assertEqual(package["workflow"], "v1_product_package")
        self.assertEqual(package["current_phase"], "REALIZE")
        self.assertEqual(package["status"], "WAITING_FOR_GATE")
        output_types = {output["output_type"] for output in package["included_outputs"]}
        self.assertIn("evaluation_report", output_types)
        self.assertIn("gtm_report", output_types)
        self.assertIn("financial_report", output_types)


if __name__ == "__main__":
    unittest.main()

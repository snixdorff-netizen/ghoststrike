import unittest

from ada_iq.agents import StubAgentRunner
from ada_iq.models import AgentSpec, DFNPhase, Project, SmartProductBrief


class ConsumerInsightsTests(unittest.TestCase):
    def test_consumer_insights_agent_uses_provider_backed_output(self) -> None:
        runner = StubAgentRunner()
        project = Project(
            name="Cole Haan Pilot",
            brief=(
                "Launch an AI-native footwear concept targeting urban professionals who want "
                "adaptable comfort and premium direct-to-consumer positioning in the United States."
            ),
        )
        spec = AgentSpec(
            "agent-2",
            "Ada Empath",
            "Consumer Insights Agent",
            DFNPhase.EMPATHIZE,
            "Persona and need-state analysis.",
        )

        output = runner.run(project, spec)

        self.assertEqual(output.output_type, "consumer_insights_report")
        self.assertEqual(output.data["integration_mode"], "provider_backed_mock")
        self.assertEqual(output.data["primary_persona"]["name"], "Performance-Driven Professional")
        self.assertEqual(output.data["primary_persona"]["occasion"], "work-to-evening transitions")
        self.assertEqual(output.data["sentiment_mix"]["positive"], 0.58)
        self.assertIn("urban professionals", output.data["insight_statements"][0].lower())
        self.assertTrue(output.data["citations"])
        self.assertTrue(output.data["source_highlights"])
        self.assertIn("recommended_next_action", output.data)

    def test_consumer_insights_prefers_structured_smart_brief_fields(self) -> None:
        runner = StubAgentRunner()
        project = Project(
            name="Trail Demo",
            brief="Generic fallback brief text.",
            smart_brief=SmartProductBrief(
                category="Trail running footwear",
                price_point="$165",
                consumer_profile="Experienced trail runners",
                geo_market="United States specialty run",
                competitive_set=["Hoka Speedgoat", "Salomon Genesis"],
                brand_guardrails="Premium performance",
                constraints="Spring line review",
                launch_season="Spring 2027",
                open_context="Need lightweight grip, comfort, and confidence over technical terrain.",
            ),
        )
        spec = AgentSpec(
            "agent-2",
            "Ada Empath",
            "Consumer Insights Agent",
            DFNPhase.EMPATHIZE,
            "Persona and need-state analysis.",
        )

        output = runner.run(project, spec)

        self.assertEqual(output.data["primary_persona"]["segment"], "Experienced trail runners")
        self.assertEqual(output.data["primary_persona"]["occasion"], "high-exertion outdoor sessions")
        self.assertEqual(output.data["primary_persona"]["job_to_be_done"], "all-day comfort without sacrificing premium perception")


if __name__ == "__main__":
    unittest.main()

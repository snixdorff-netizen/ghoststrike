import unittest

from ada_iq.agents import StubAgentRunner
from ada_iq.models import AgentSpec, DFNPhase, Project, SmartProductBrief


class MarketIntelligenceTests(unittest.TestCase):
    def test_market_intelligence_agent_uses_provider_backed_output(self) -> None:
        runner = StubAgentRunner()
        project = Project(
            name="Cole Haan Pilot",
            brief=(
                "Launch an AI-native footwear concept targeting urban professionals who want "
                "adaptable comfort and premium direct-to-consumer positioning in the United States."
            ),
        )
        spec = AgentSpec(
            "agent-1",
            "Ada Scout",
            "Market Intelligence Agent",
            DFNPhase.EMPATHIZE,
            "Market sizing and trend analysis.",
        )

        output = runner.run(project, spec)

        self.assertEqual(output.output_type, "market_intelligence_report")
        self.assertEqual(output.data["integration_mode"], "provider_backed_mock")
        self.assertEqual(output.data["geography_focus"], "North America")
        self.assertIn("Cole Haan Pilot", output.data["summary"])
        self.assertGreater(output.data["tam_sam_som"]["tam_billion_usd"], 50.0)
        self.assertIn("Nike", output.data["top_competitors"])
        self.assertTrue(output.data["citations"])
        self.assertTrue(output.data["source_highlights"])
        self.assertIn("recommended_next_action", output.data)

    def test_market_intelligence_prefers_structured_smart_brief_fields(self) -> None:
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
                open_context="Need lightweight grip and comfort on technical terrain.",
            ),
        )
        spec = AgentSpec(
            "agent-1",
            "Ada Scout",
            "Market Intelligence Agent",
            DFNPhase.EMPATHIZE,
            "Market sizing and trend analysis.",
        )

        output = runner.run(project, spec)

        self.assertEqual(output.data["geography_focus"], "United States specialty run")
        self.assertEqual(output.data["target_segment"], "Experienced trail runners")
        self.assertEqual(output.data["top_competitors"], ["Hoka Speedgoat", "Salomon Genesis"])


if __name__ == "__main__":
    unittest.main()

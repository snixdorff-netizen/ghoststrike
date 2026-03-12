from __future__ import annotations

from abc import ABC, abstractmethod


class GTMProvider(ABC):
    @abstractmethod
    def analyze(self, project_name: str, brief: str) -> dict:
        raise NotImplementedError


class MockGTMProvider(GTMProvider):
    """Deterministic go-to-market planning adapter."""

    def analyze(self, project_name: str, brief: str) -> dict:
        channel = "premium DTC" if "direct-to-consumer" in brief.lower() or "premium" in brief.lower() else "hybrid retail"
        return {
            "confidence_score": 0.69,
            "sources": ["human_project_brief", "mock_gtm_provider"],
            "data": {
                "summary": f"Ada Launcher assembled a {channel} launch plan for {project_name}.",
                "integration_mode": "provider_backed_mock",
                "launch_channel": channel,
                "launch_sequence": [
                    "pre-launch waitlist and narrative testing",
                    "launch-week creator and retention content",
                    "post-launch referral and proof expansion",
                ],
                "customer_journey": [
                    "discover",
                    "compare",
                    "validate premium value",
                    "purchase",
                    "repeat/referral",
                ],
                "recommended_questions": [
                    "Which channel should carry the first launch narrative?",
                    "What proof asset best reduces hesitation at point of purchase?",
                ],
            },
        }

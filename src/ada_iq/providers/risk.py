from __future__ import annotations

from abc import ABC, abstractmethod


class RiskProvider(ABC):
    @abstractmethod
    def analyze(self, project_name: str, brief: str) -> dict:
        raise NotImplementedError


class MockRiskProvider(RiskProvider):
    """Deterministic risk-planning adapter."""

    def analyze(self, project_name: str, brief: str) -> dict:
        premium = "premium" in brief.lower()
        return {
            "confidence_score": 0.66,
            "sources": ["human_project_brief", "mock_risk_provider"],
            "data": {
                "summary": f"Ada Guardian produced a risk register for {project_name} across market, operational, and financial categories.",
                "integration_mode": "provider_backed_mock",
                "top_risks": [
                    {"category": "market", "score": 16 if premium else 14, "mitigation": "tighten first-segment positioning"},
                    {"category": "operational", "score": 12, "mitigation": "stage supplier and fulfillment dependencies"},
                    {"category": "financial", "score": 10, "mitigation": "hold CAC guardrails and payback thresholds"},
                ],
                "recommended_questions": [
                    "Which leading indicator should trigger a launch-plan adjustment first?",
                    "Which mitigation step most reduces downside without slowing learning?",
                ],
            },
        }

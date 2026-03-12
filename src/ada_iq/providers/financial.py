from __future__ import annotations

from abc import ABC, abstractmethod


class FinancialProvider(ABC):
    @abstractmethod
    def analyze(self, project_name: str, brief: str) -> dict:
        raise NotImplementedError


class MockFinancialProvider(FinancialProvider):
    """Deterministic financial planning adapter."""

    def analyze(self, project_name: str, brief: str) -> dict:
        premium = "premium" in brief.lower()
        return {
            "confidence_score": 0.67,
            "sources": ["human_project_brief", "mock_financial_provider"],
            "data": {
                "summary": f"Ada Banker modeled a {'premium' if premium else 'standard'} unit-economics case for {project_name}.",
                "integration_mode": "provider_backed_mock",
                "unit_economics": {
                    "gross_margin": 0.68 if premium else 0.58,
                    "ltv_cac_ratio": 3.4 if premium else 2.6,
                    "payback_months": 5 if premium else 8,
                },
                "three_year_projection_musd": {
                    "conservative": 1.8,
                    "moderate": 4.2,
                    "aggressive": 8.7,
                },
                "recommended_questions": [
                    "What assumption has the largest impact on CAC payback?",
                    "What launch volume is required to validate the moderate case?",
                ],
            },
        }

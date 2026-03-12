from __future__ import annotations

from abc import ABC, abstractmethod


class EvaluationProvider(ABC):
    @abstractmethod
    def analyze(self, project_name: str, brief: str) -> dict:
        raise NotImplementedError


class MockEvaluationProvider(EvaluationProvider):
    """Deterministic concept-evaluation adapter."""

    def analyze(self, project_name: str, brief: str) -> dict:
        score = 0.84 if "premium" in brief.lower() else 0.77
        return {
            "confidence_score": 0.73,
            "sources": ["human_project_brief", "mock_evaluation_provider", "dmde_style_scoring_mock"],
            "data": {
                "summary": f"Ada Judge scored the lead concept for {project_name} and recommended prototype progression.",
                "integration_mode": "provider_backed_mock",
                "lead_concept_score": score,
                "decision": "advance_to_realization" if score >= 0.8 else "refine_before_realization",
                "score_breakdown": {
                    "desirability": round(score, 2),
                    "differentiation": 0.74,
                    "feasibility": 0.7,
                },
                "recommended_questions": [
                    "What prototype evidence would most improve feasibility confidence?",
                    "Which concept weakness can be resolved without diluting the core value proposition?",
                ],
            },
        }

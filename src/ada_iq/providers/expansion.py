from __future__ import annotations

from abc import ABC, abstractmethod


class ExpansionProvider(ABC):
    @abstractmethod
    def analyze(self, project_name: str, brief: str) -> dict:
        raise NotImplementedError


class MockExpansionProvider(ExpansionProvider):
    """Deterministic expansion-planning adapter."""

    def analyze(self, project_name: str, brief: str) -> dict:
        geography = "North America first" if "united states" in brief.lower() else "Domestic wedge first"
        return {
            "confidence_score": 0.64,
            "sources": ["human_project_brief", "mock_expansion_provider"],
            "data": {
                "summary": f"Ada Explorer mapped the most plausible expansion path for {project_name}.",
                "integration_mode": "provider_backed_mock",
                "expansion_priority": geography,
                "candidate_paths": [
                    {"path": "adjacent premium segment", "attractiveness": 0.78},
                    {"path": "select retail partnership", "attractiveness": 0.69},
                    {"path": "international expansion", "attractiveness": 0.57},
                ],
                "recommended_questions": [
                    "What must be true before the second market or segment opens?",
                    "Which partnership model creates the best learning leverage?",
                ],
            },
        }

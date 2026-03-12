from __future__ import annotations

from abc import ABC, abstractmethod


class ConceptGenerationProvider(ABC):
    @abstractmethod
    def analyze(self, project_name: str, brief: str) -> dict:
        raise NotImplementedError


class MockConceptGenerationProvider(ConceptGenerationProvider):
    """Deterministic concept-generation adapter for early-step walkthroughs."""

    def analyze(self, project_name: str, brief: str) -> dict:
        family = self._family(brief)
        concepts = self._concepts(project_name, family)
        return {
            "confidence_score": 0.68,
            "sources": [
                "human_project_brief",
                "mock_concept_generation_provider",
                f"family:{family.lower().replace(' ', '_')}",
            ],
            "data": {
                "summary": f"Ada Creator generated three concept directions for {project_name} in the {family} family.",
                "integration_mode": "provider_backed_mock",
                "concept_family": family,
                "shortlisted_concepts": concepts,
                "recommended_direction": concepts[0]["name"],
                "recommended_questions": [
                    "Which concept direction best balances novelty with brand fit?",
                    "Which concept should move into prototype scoring first?",
                ],
            },
        }

    def _family(self, brief: str) -> str:
        lower = brief.lower()
        if "footwear" in lower or "shoe" in lower:
            return "adaptive comfort systems"
        if "kitchen" in lower or "appliance" in lower:
            return "guided prep workflows"
        if "hydration" in lower or "trail" in lower:
            return "modular endurance gear"
        return "functional wedge concepts"

    def _concepts(self, project_name: str, family: str) -> list[dict]:
        base = project_name.split()[0]
        return [
            {"name": f"{base} Core", "desirability_score": 0.82, "rationale": f"Closest-to-market expression of {family}."},
            {"name": f"{base} Flex", "desirability_score": 0.76, "rationale": "Balances differentiation with easier launch execution."},
            {"name": f"{base} Edge", "desirability_score": 0.71, "rationale": "More novel direction with higher brand risk and upside."},
        ]

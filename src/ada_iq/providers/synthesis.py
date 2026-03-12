from __future__ import annotations

from abc import ABC, abstractmethod


class SynthesisProvider(ABC):
    @abstractmethod
    def analyze(self, project_name: str, brief: str) -> dict:
        raise NotImplementedError


class MockSynthesisProvider(SynthesisProvider):
    """Deterministic executive-synthesis adapter."""

    def analyze(self, project_name: str, brief: str) -> dict:
        return {
            "confidence_score": 0.71,
            "sources": ["human_project_brief", "mock_synthesis_provider"],
            "data": {
                "summary": f"Ada Synthesizer assembled the executive recommendation package for {project_name}.",
                "integration_mode": "provider_backed_mock",
                "preferred_option": "Proceed with a focused pilot and premium wedge positioning.",
                "strategic_options": [
                    {"name": "focused pilot", "pros": "highest learning density", "cons": "slower scale"},
                    {"name": "broader launch", "pros": "faster top-line signal", "cons": "weaker message clarity"},
                    {"name": "partner-led rollout", "pros": "reduced channel risk", "cons": "lower direct customer insight"},
                ],
                "next_best_actions": [
                    "Approve prototype and launch-asset build",
                    "Validate willingness-to-pay with live prospects",
                    "Track CAC payback and risk indicators in the pilot window",
                ],
                "recommended_questions": [
                    "Which executive decision is still blocked by missing evidence?",
                    "What is the single most important proof point for the next gate?",
                ],
            },
        }

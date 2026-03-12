from __future__ import annotations

import re
from abc import ABC, abstractmethod


class ConsumerInsightsProvider(ABC):
    @abstractmethod
    def analyze(self, project_name: str, brief: str) -> dict:
        raise NotImplementedError


class MockConsumerInsightsProvider(ConsumerInsightsProvider):
    """Deterministic provider that mimics an external consumer-insights stack."""

    def analyze(self, project_name: str, brief: str) -> dict:
        segment = self._extract_segment(brief)
        need_state = self._extract_need_state(brief)
        occasion = self._extract_occasion(brief)
        sentiment = self._sentiment_mix(brief)

        return {
            "confidence_score": 0.72,
            "sources": [
                "human_project_brief",
                "mock_consumer_insights_provider",
                f"segment:{segment.lower().replace(' ', '_')}",
            ],
            "data": {
                "summary": (
                    f"Ada Empath synthesized an initial persona for {project_name}, centering on {segment} "
                    f"who need {need_state} in {occasion} moments."
                ),
                "integration_mode": "provider_backed_mock",
                "primary_persona": {
                    "name": self._persona_name(segment),
                    "segment": segment,
                    "job_to_be_done": need_state,
                    "occasion": occasion,
                },
                "need_hierarchy": [
                    {"need": need_state, "priority": 1},
                    {"need": "confidence in purchase quality", "priority": 2},
                    {"need": "clear fit with lifestyle identity", "priority": 3},
                ],
                "sentiment_mix": sentiment,
                "insight_statements": [
                    f"{segment} need {need_state} because their daily routine punishes friction, but current options force visible compromise.",
                    f"{segment} want products that signal competence and good taste, but they distrust feature-heavy positioning without proof.",
                ],
                "recommended_questions": [
                    "Which persona assumptions need live interview validation first?",
                    "What evidence would show this need hierarchy is wrong?",
                    "Which use occasion should anchor the first prototype narrative?",
                ],
            },
        }

    def _extract_segment(self, brief: str) -> str:
        match = re.search(r"targeting ([^.]+?)(?: who| with| focused|\.|,)", brief, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        match = re.search(r"for ([^.]+?)(?: with| focused|\.|,)", brief, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "time-constrained professionals"

    def _extract_need_state(self, brief: str) -> str:
        lower = brief.lower()
        if "comfort" in lower:
            return "all-day comfort without sacrificing premium perception"
        if "lightweight" in lower or "cold-weather" in lower:
            return "reliable performance under changing conditions"
        if "safety" in lower or "ergonomic" in lower:
            return "safe, intuitive use in busy environments"
        return "clear functional improvement over incumbent products"

    def _extract_occasion(self, brief: str) -> str:
        lower = brief.lower()
        if "urban professionals" in lower or "professional" in lower:
            return "work-to-evening transitions"
        if "trail" in lower or "runner" in lower:
            return "high-exertion outdoor sessions"
        if "household" in lower or "kitchen" in lower:
            return "weekday meal-prep routines"
        return "repeat high-friction daily routines"

    def _sentiment_mix(self, brief: str) -> dict[str, float]:
        lower = brief.lower()
        if "premium" in lower:
            return {"positive": 0.58, "neutral": 0.27, "negative": 0.15}
        if "safety" in lower:
            return {"positive": 0.49, "neutral": 0.33, "negative": 0.18}
        return {"positive": 0.52, "neutral": 0.29, "negative": 0.19}

    def _persona_name(self, segment: str) -> str:
        if "professional" in segment.lower():
            return "Performance-Driven Professional"
        if "runner" in segment.lower():
            return "Committed Endurance Athlete"
        if "household" in segment.lower():
            return "Efficiency-Focused Home Operator"
        return "High-Intent Category Adopter"

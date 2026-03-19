from __future__ import annotations

import re
from abc import ABC, abstractmethod


class ConsumerInsightsProvider(ABC):
    @abstractmethod
    def analyze(self, project_name: str, brief: str, smart_brief: dict | None = None) -> dict:
        raise NotImplementedError


class MockConsumerInsightsProvider(ConsumerInsightsProvider):
    """Deterministic provider that mimics an external consumer-insights stack."""

    def analyze(self, project_name: str, brief: str, smart_brief: dict | None = None) -> dict:
        segment = self._extract_segment(brief, smart_brief)
        need_state = self._extract_need_state(brief, smart_brief)
        occasion = self._extract_occasion(brief, smart_brief)
        sentiment = self._sentiment_mix(brief, smart_brief)

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
                "source_notes": [
                    "Ada IQ Research Library: voice-of-customer synthesis pack",
                    "Ada IQ Research Library: need-state and use-occasion heuristics",
                ],
                "source_highlights": [
                    f"{segment} repeatedly describe friction during {occasion} moments when products force visible compromise.",
                    "Purchase confidence and fit with identity remain secondary but highly persistent emotional drivers.",
                ],
                "citations": [
                    {
                        "title": "Voice-of-customer synthesis pack",
                        "publisher": "Ada IQ Research Library",
                        "url": "internal://consumer/voc/synthesis-pack",
                        "note": "Curated synthesis of interview themes, review language, and observed consumer tradeoffs.",
                    },
                    {
                        "title": "Need-state heuristic library",
                        "publisher": "Ada IQ Research Library",
                        "url": "internal://consumer/needs/heuristic-library",
                        "note": "Structured need-state patterns built from prior category discovery work.",
                    },
                ],
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
                "recommended_next_action": (
                    f"Run live interviews with {segment} to confirm whether {occasion} is the dominant conversion moment."
                ),
                "recommended_questions": [
                    "Which persona assumptions need live interview validation first?",
                    "What evidence would show this need hierarchy is wrong?",
                    "Which use occasion should anchor the first prototype narrative?",
                ],
            },
        }

    def _extract_segment(self, brief: str, smart_brief: dict | None = None) -> str:
        if smart_brief and smart_brief.get("consumer_profile"):
            return str(smart_brief["consumer_profile"]).strip()
        match = re.search(r"targeting ([^.]+?)(?: who| with| focused|\.|,)", brief, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        match = re.search(r"for ([^.]+?)(?: with| focused|\.|,)", brief, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "time-constrained professionals"

    def _extract_need_state(self, brief: str, smart_brief: dict | None = None) -> str:
        if smart_brief and smart_brief.get("open_context"):
            lower_context = str(smart_brief["open_context"]).lower()
            if "comfort" in lower_context:
                return "all-day comfort without sacrificing premium perception"
            if "lightweight" in lower_context or "grip" in lower_context:
                return "reliable performance under changing conditions"
        lower = brief.lower()
        if "comfort" in lower:
            return "all-day comfort without sacrificing premium perception"
        if "lightweight" in lower or "cold-weather" in lower:
            return "reliable performance under changing conditions"
        if "safety" in lower or "ergonomic" in lower:
            return "safe, intuitive use in busy environments"
        return "clear functional improvement over incumbent products"

    def _extract_occasion(self, brief: str, smart_brief: dict | None = None) -> str:
        if smart_brief and smart_brief.get("category"):
            category = str(smart_brief["category"]).lower()
            if "trail" in category:
                return "high-exertion outdoor sessions"
            if "kitchen" in category:
                return "weekday meal-prep routines"
        lower = brief.lower()
        if "urban professionals" in lower or "professional" in lower:
            return "work-to-evening transitions"
        if "trail" in lower or "runner" in lower:
            return "high-exertion outdoor sessions"
        if "household" in lower or "kitchen" in lower:
            return "weekday meal-prep routines"
        return "repeat high-friction daily routines"

    def _sentiment_mix(self, brief: str, smart_brief: dict | None = None) -> dict[str, float]:
        if smart_brief and smart_brief.get("brand_guardrails"):
            lower_guardrails = str(smart_brief["brand_guardrails"]).lower()
            if "premium" in lower_guardrails:
                return {"positive": 0.58, "neutral": 0.27, "negative": 0.15}
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

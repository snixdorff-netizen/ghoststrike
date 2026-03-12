from __future__ import annotations

import re
from abc import ABC, abstractmethod


class StrategyProvider(ABC):
    @abstractmethod
    def analyze(self, project_name: str, brief: str) -> dict:
        raise NotImplementedError


class MockStrategyProvider(StrategyProvider):
    """Deterministic strategy adapter for early product-development steps."""

    def analyze(self, project_name: str, brief: str) -> dict:
        segment = self._extract_segment(brief)
        price_position = self._price_position(brief)
        opportunity = self._opportunity(brief)

        return {
            "confidence_score": 0.7,
            "sources": [
                "human_project_brief",
                "mock_strategy_provider",
                f"segment:{segment.lower().replace(' ', '_')}",
            ],
            "data": {
                "summary": (
                    f"Ada Strategist translated the EMPATHIZE findings for {project_name} into a "
                    f"{price_position} strategy centered on {opportunity}."
                ),
                "integration_mode": "provider_backed_mock",
                "swot": {
                    "strengths": ["clear user pain point", "premium positioning potential"],
                    "weaknesses": ["needs stronger proof of differentiation", "limited initial brand trust"],
                    "opportunities": [opportunity, "focused wedge launch by high-intent segment"],
                    "threats": ["incumbent copycats", "price sensitivity under weak messaging"],
                },
                "pricing_strategy": {
                    "position": price_position,
                    "recommended_range_usd": self._price_range(brief),
                },
                "how_might_we": [
                    f"How might we deliver {opportunity} for {segment} without adding unnecessary complexity?",
                    "How might we make premium value legible in the first 30 seconds of product exposure?",
                ],
                "opportunity_map": [
                    {"name": "focused launch wedge", "effort": "medium", "impact": "high"},
                    {"name": "premium narrative proof", "effort": "low", "impact": "high"},
                    {"name": "adjacent-market expansion", "effort": "high", "impact": "medium"},
                ],
                "recommended_questions": [
                    "Which opportunity should get prototype resources first?",
                    "What price ceiling still preserves conversion confidence?",
                ],
            },
        }

    def _extract_segment(self, brief: str) -> str:
        match = re.search(r"targeting ([^.]+?)(?: who| with| focused|\.|,)", brief, re.IGNORECASE)
        return match.group(1).strip() if match else "high-intent launch customers"

    def _price_position(self, brief: str) -> str:
        lower = brief.lower()
        if "premium" in lower:
            return "premium"
        if "value" in lower or "affordable" in lower:
            return "accessible-premium"
        return "mid-premium"

    def _opportunity(self, brief: str) -> str:
        lower = brief.lower()
        if "comfort" in lower:
            return "premium comfort that does not look compromised"
        if "safety" in lower:
            return "safer use with lower cognitive load"
        if "lightweight" in lower:
            return "performance reliability with lower carry burden"
        return "clear functional improvement over incumbent options"

    def _price_range(self, brief: str) -> list[int]:
        lower = brief.lower()
        if "footwear" in lower or "shoe" in lower:
            return [145, 210]
        if "kitchen" in lower or "appliance" in lower:
            return [180, 320]
        return [75, 160]

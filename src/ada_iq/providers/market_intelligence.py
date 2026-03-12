from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class MarketProfile:
    label: str
    tam_billions: float
    sam_share: float
    som_share: float
    cagr: float
    competitors: tuple[str, ...]
    trends: tuple[str, ...]
    whitespace: str


PROFILES: dict[str, MarketProfile] = {
    "footwear": MarketProfile(
        label="premium footwear",
        tam_billions=92.0,
        sam_share=0.16,
        som_share=0.015,
        cagr=0.082,
        competitors=("Nike", "On Running", "Allbirds", "Cole Haan"),
        trends=("hybrid comfort", "sustainable materials", "premium direct-to-consumer"),
        whitespace="Professional footwear that blends dress aesthetics with recovery-level comfort.",
    ),
    "hydration": MarketProfile(
        label="performance hydration gear",
        tam_billions=14.5,
        sam_share=0.19,
        som_share=0.018,
        cagr=0.094,
        competitors=("CamelBak", "Salomon", "Osprey", "Nathan Sports"),
        trends=("lightweight modularity", "cold-weather usability", "premium trail accessories"),
        whitespace="Hydration systems optimized for temperature shifts and fast refills during endurance events.",
    ),
    "kitchen": MarketProfile(
        label="smart kitchen appliances",
        tam_billions=38.0,
        sam_share=0.13,
        som_share=0.012,
        cagr=0.071,
        competitors=("Ninja", "Instant", "Breville", "KitchenAid"),
        trends=("countertop consolidation", "safety-led design", "connected meal prep"),
        whitespace="Compact prep systems that reduce setup friction for time-constrained households.",
    ),
    "default": MarketProfile(
        label="adjacent consumer product market",
        tam_billions=21.0,
        sam_share=0.12,
        som_share=0.01,
        cagr=0.063,
        competitors=("Category incumbent A", "Category incumbent B", "Premium challenger C"),
        trends=("specialized premiumization", "channel fragmentation", "utility-led brand differentiation"),
        whitespace="A focused offer for a high-intent customer segment underserved by generic incumbents.",
    ),
}


class MarketIntelligenceProvider(ABC):
    @abstractmethod
    def analyze(self, project_name: str, brief: str) -> dict:
        raise NotImplementedError


class MockMarketIntelligenceProvider(MarketIntelligenceProvider):
    """Deterministic provider that mimics an external research service boundary."""

    def analyze(self, project_name: str, brief: str) -> dict:
        profile = self._pick_profile(brief)
        segment = self._extract_segment(brief)
        geography = self._extract_geography(brief)

        tam = profile.tam_billions
        sam = round(tam * profile.sam_share, 2)
        som = round(sam * profile.som_share, 2)
        confidence = 0.74 if profile.label != PROFILES["default"].label else 0.61

        return {
            "confidence_score": confidence,
            "sources": [
                "human_project_brief",
                "mock_market_intelligence_provider",
                f"profile:{profile.label}",
            ],
            "data": {
                "summary": (
                    f"Ada Scout produced a structured market read for {project_name}, estimating a "
                    f"${tam:.1f}B TAM with strongest traction in {segment} buyers."
                ),
                "integration_mode": "provider_backed_mock",
                "market_profile": profile.label,
                "geography_focus": geography,
                "target_segment": segment,
                "tam_sam_som": {
                    "tam_billion_usd": tam,
                    "sam_billion_usd": sam,
                    "som_billion_usd": som,
                },
                "five_year_cagr": profile.cagr,
                "top_competitors": list(profile.competitors),
                "trend_signals": list(profile.trends),
                "whitespace_opportunity": profile.whitespace,
                "recommended_questions": [
                    "Which wedge segment should the launch prioritize first?",
                    "What evidence would invalidate the current market sizing assumptions?",
                    "Which competitor should define the baseline comparison set?",
                ],
            },
        }

    def _pick_profile(self, brief: str) -> MarketProfile:
        lower_brief = brief.lower()
        if any(term in lower_brief for term in ("shoe", "footwear", "sneaker", "loafer")):
            return PROFILES["footwear"]
        if any(term in lower_brief for term in ("hydration", "trail", "runner", "bottle")):
            return PROFILES["hydration"]
        if any(term in lower_brief for term in ("kitchen", "countertop", "prep", "appliance")):
            return PROFILES["kitchen"]
        return PROFILES["default"]

    def _extract_segment(self, brief: str) -> str:
        match = re.search(r"targeting ([^.]+?)(?: who| with| focused|\.|,)", brief, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        match = re.search(r"for ([^.]+?)(?: with| focused|\.|,)", brief, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "high-intent early adopters"

    def _extract_geography(self, brief: str) -> str:
        lower_brief = brief.lower()
        if "us" in lower_brief or "united states" in lower_brief or "north america" in lower_brief:
            return "North America"
        if "europe" in lower_brief or "eu" in lower_brief:
            return "Europe"
        return "Initial domestic launch"

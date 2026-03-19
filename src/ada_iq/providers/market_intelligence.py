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
    citations: tuple[dict[str, str], ...]


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
        citations=(
            {
                "title": "Premium footwear category scan",
                "publisher": "Ada IQ Research Library",
                "url": "internal://market/footwear/category-scan",
                "note": "Benchmarks premiumization, DTC behavior, and comfort-led differentiation in footwear.",
            },
            {
                "title": "Professional lifestyle segment brief",
                "publisher": "Ada IQ Research Library",
                "url": "internal://market/footwear/professional-segment",
                "note": "Profiles urban professionals balancing style, comfort, and daily wear frequency.",
            },
        ),
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
        citations=(
            {
                "title": "Endurance accessories market brief",
                "publisher": "Ada IQ Research Library",
                "url": "internal://market/hydration/endurance-accessories",
                "note": "Summarizes trail, run, and endurance-hydration accessory purchasing signals.",
            },
            {
                "title": "Outdoor specialty channel tracker",
                "publisher": "Ada IQ Research Library",
                "url": "internal://market/hydration/channel-tracker",
                "note": "Maps product positioning across specialty outdoor and direct-to-consumer channels.",
            },
        ),
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
        citations=(
            {
                "title": "Countertop appliance trend digest",
                "publisher": "Ada IQ Research Library",
                "url": "internal://market/kitchen/countertop-digest",
                "note": "Tracks consolidation, convenience, and safety narratives in countertop appliances.",
            },
            {
                "title": "Home efficiency need-state review",
                "publisher": "Ada IQ Research Library",
                "url": "internal://market/kitchen/efficiency-needs",
                "note": "Synthesizes weekday meal-prep pain points and design constraints for busy households.",
            },
        ),
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
        citations=(
            {
                "title": "Adjacent category market overview",
                "publisher": "Ada IQ Research Library",
                "url": "internal://market/default/category-overview",
                "note": "General benchmark pack for emerging consumer-product categories.",
            },
            {
                "title": "Premium challenger playbook",
                "publisher": "Ada IQ Research Library",
                "url": "internal://market/default/challenger-playbook",
                "note": "Examples of premium challenger brands winning on specificity and differentiated positioning.",
            },
        ),
    ),
}


class MarketIntelligenceProvider(ABC):
    @abstractmethod
    def analyze(self, project_name: str, brief: str, smart_brief: dict | None = None) -> dict:
        raise NotImplementedError


class MockMarketIntelligenceProvider(MarketIntelligenceProvider):
    """Deterministic provider that mimics an external research service boundary."""

    def analyze(self, project_name: str, brief: str, smart_brief: dict | None = None) -> dict:
        profile = self._pick_profile(brief, smart_brief)
        segment = self._extract_segment(brief, smart_brief)
        geography = self._extract_geography(brief, smart_brief)
        competitive_set = self._extract_competitors(profile, smart_brief)

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
                "source_notes": [
                    f"{citation['publisher']}: {citation['title']}"
                    for citation in profile.citations
                ],
                "source_highlights": [
                    f"{profile.label.title()} demand is being shaped by {profile.trends[0]} and {profile.trends[1]} positioning."
                    if len(profile.trends) > 1
                    else f"{profile.label.title()} demand is showing premiumization pressure."
                ],
                "citations": list(profile.citations),
                "market_profile": profile.label,
                "geography_focus": geography,
                "target_segment": segment,
                "tam_sam_som": {
                    "tam_billion_usd": tam,
                    "sam_billion_usd": sam,
                    "som_billion_usd": som,
                },
                "five_year_cagr": profile.cagr,
                "top_competitors": competitive_set,
                "trend_signals": list(profile.trends),
                "whitespace_opportunity": profile.whitespace,
                "recommended_next_action": (
                    f"Validate the {segment} wedge with real buyers before expanding the competitor comparison set."
                ),
                "recommended_questions": [
                    "Which wedge segment should the launch prioritize first?",
                    "What evidence would invalidate the current market sizing assumptions?",
                    "Which competitor should define the baseline comparison set?",
                ],
            },
        }

    def _pick_profile(self, brief: str, smart_brief: dict | None = None) -> MarketProfile:
        category = str((smart_brief or {}).get("category", "")).lower()
        if "footwear" in category or "shoe" in category:
            return PROFILES["footwear"]
        if "hydration" in category or "trail" in category:
            return PROFILES["hydration"]
        if "kitchen" in category or "appliance" in category:
            return PROFILES["kitchen"]
        lower_brief = brief.lower()
        if any(term in lower_brief for term in ("shoe", "footwear", "sneaker", "loafer")):
            return PROFILES["footwear"]
        if any(term in lower_brief for term in ("hydration", "trail", "runner", "bottle")):
            return PROFILES["hydration"]
        if any(term in lower_brief for term in ("kitchen", "countertop", "prep", "appliance")):
            return PROFILES["kitchen"]
        return PROFILES["default"]

    def _extract_segment(self, brief: str, smart_brief: dict | None = None) -> str:
        if smart_brief and smart_brief.get("consumer_profile"):
            return str(smart_brief["consumer_profile"]).strip()
        match = re.search(r"targeting ([^.]+?)(?: who| with| focused|\.|,)", brief, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        match = re.search(r"for ([^.]+?)(?: with| focused|\.|,)", brief, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "high-intent early adopters"

    def _extract_geography(self, brief: str, smart_brief: dict | None = None) -> str:
        if smart_brief and smart_brief.get("geo_market"):
            return str(smart_brief["geo_market"]).strip()
        lower_brief = brief.lower()
        if "us" in lower_brief or "united states" in lower_brief or "north america" in lower_brief:
            return "North America"
        if "europe" in lower_brief or "eu" in lower_brief:
            return "Europe"
        return "Initial domestic launch"

    def _extract_competitors(self, profile: MarketProfile, smart_brief: dict | None = None) -> list[str]:
        if smart_brief and smart_brief.get("competitive_set"):
            return [str(item).strip() for item in smart_brief["competitive_set"] if str(item).strip()]
        return list(profile.competitors)

from __future__ import annotations

from dataclasses import asdict

from ada_iq.models import AgentOutput, AgentSpec, DFNPhase, Project
from ada_iq.providers.concept_generation import ConceptGenerationProvider, MockConceptGenerationProvider
from ada_iq.providers.consumer_insights import ConsumerInsightsProvider, MockConsumerInsightsProvider
from ada_iq.providers.expansion import ExpansionProvider, MockExpansionProvider
from ada_iq.providers.evaluation import EvaluationProvider, MockEvaluationProvider
from ada_iq.providers.financial import FinancialProvider, MockFinancialProvider
from ada_iq.providers.gtm import GTMProvider, MockGTMProvider
from ada_iq.providers.market_intelligence import MarketIntelligenceProvider, MockMarketIntelligenceProvider
from ada_iq.providers.risk import MockRiskProvider, RiskProvider
from ada_iq.providers.strategy import MockStrategyProvider, StrategyProvider
from ada_iq.providers.synthesis import MockSynthesisProvider, SynthesisProvider


AGENT_SPECS: tuple[AgentSpec, ...] = (
    AgentSpec("agent-1", "Ada Scout", "Market Intelligence Agent", DFNPhase.EMPATHIZE, "Market sizing and trend analysis."),
    AgentSpec("agent-2", "Ada Empath", "Consumer Insights Agent", DFNPhase.EMPATHIZE, "Persona and need-state analysis."),
    AgentSpec("agent-3", "Ada Watcher", "Competitive Intel Agent", DFNPhase.EMPATHIZE, "Competitive monitoring and battle cards."),
    AgentSpec("agent-4", "Ada Strategist", "Strategy Agent", DFNPhase.IDEATE, "SWOT, Porter, pricing, and opportunity mapping."),
    AgentSpec("agent-5", "Ada Creator", "Concept Generation Agent", DFNPhase.IDEATE, "Concept generation and clustering."),
    AgentSpec("agent-6", "Ada Judge", "Evaluation Agent", DFNPhase.EVALUATE, "Concept desirability scoring and validation."),
    AgentSpec("agent-7", "Ada Builder", "CAD Integration Agent", DFNPhase.REALIZE, "CAD realization and DFN scoring hooks."),
    AgentSpec("agent-8", "Ada Launcher", "GTM Agent", DFNPhase.REALIZE, "Launch planning and customer journey mapping."),
    AgentSpec("agent-9", "Ada Banker", "Financial Agent", DFNPhase.REALIZE, "Unit economics and scenario modeling."),
    AgentSpec("agent-10", "Ada Guardian", "Risk Agent", DFNPhase.MEASURE, "Risk scoring and mitigation planning."),
    AgentSpec("agent-11", "Ada Explorer", "Expansion Agent", DFNPhase.MEASURE, "Expansion pathway evaluation."),
    AgentSpec("agent-12", "Ada Synthesizer", "Synthesis Agent", DFNPhase.MEASURE, "Executive recommendation synthesis."),
)


PHASE_TO_AGENTS: dict[DFNPhase, list[AgentSpec]] = {}
for spec in AGENT_SPECS:
    PHASE_TO_AGENTS.setdefault(spec.phase, []).append(spec)


def list_agent_specs() -> list[dict[str, str]]:
    return [
        {
            "agent_id": spec.agent_id,
            "code_name": spec.code_name,
            "display_name": spec.display_name,
            "phase": spec.phase.value,
            "description": spec.description,
        }
        for spec in AGENT_SPECS
    ]


class StubAgentRunner:
    """Deterministic placeholder for specialist agent behavior."""

    def __init__(
        self,
        market_provider: MarketIntelligenceProvider | None = None,
        consumer_provider: ConsumerInsightsProvider | None = None,
        strategy_provider: StrategyProvider | None = None,
        concept_provider: ConceptGenerationProvider | None = None,
        evaluation_provider: EvaluationProvider | None = None,
        gtm_provider: GTMProvider | None = None,
        financial_provider: FinancialProvider | None = None,
        risk_provider: RiskProvider | None = None,
        expansion_provider: ExpansionProvider | None = None,
        synthesis_provider: SynthesisProvider | None = None,
    ) -> None:
        self.market_provider = market_provider or MockMarketIntelligenceProvider()
        self.consumer_provider = consumer_provider or MockConsumerInsightsProvider()
        self.strategy_provider = strategy_provider or MockStrategyProvider()
        self.concept_provider = concept_provider or MockConceptGenerationProvider()
        self.evaluation_provider = evaluation_provider or MockEvaluationProvider()
        self.gtm_provider = gtm_provider or MockGTMProvider()
        self.financial_provider = financial_provider or MockFinancialProvider()
        self.risk_provider = risk_provider or MockRiskProvider()
        self.expansion_provider = expansion_provider or MockExpansionProvider()
        self.synthesis_provider = synthesis_provider or MockSynthesisProvider()

    def run(self, project: Project, spec: AgentSpec) -> AgentOutput:
        smart_brief_payload = asdict(project.smart_brief) if project.smart_brief else None
        if spec.agent_id == "agent-1":
            analysis = self.market_provider.analyze(project.name, project.brief, smart_brief=smart_brief_payload)
            return AgentOutput(
                agent_id=spec.agent_id,
                output_type="market_intelligence_report",
                data={
                    "agent": asdict(spec),
                    "phase": project.current_phase.value,
                    "project_name": project.name,
                    "brief_excerpt": project.brief[:180],
                    **analysis["data"],
                },
                confidence_score=analysis["confidence_score"],
                sources=analysis["sources"],
                project_id=project.project_id,
            )
        if spec.agent_id == "agent-2":
            analysis = self.consumer_provider.analyze(project.name, project.brief, smart_brief=smart_brief_payload)
            return AgentOutput(
                agent_id=spec.agent_id,
                output_type="consumer_insights_report",
                data={
                    "agent": asdict(spec),
                    "phase": project.current_phase.value,
                    "project_name": project.name,
                    "brief_excerpt": project.brief[:180],
                    **analysis["data"],
                },
                confidence_score=analysis["confidence_score"],
                sources=analysis["sources"],
                project_id=project.project_id,
            )
        if spec.agent_id == "agent-4":
            analysis = self.strategy_provider.analyze(project.name, project.brief)
            return AgentOutput(
                agent_id=spec.agent_id,
                output_type="strategy_report",
                data={
                    "agent": asdict(spec),
                    "phase": project.current_phase.value,
                    "project_name": project.name,
                    "brief_excerpt": project.brief[:180],
                    **analysis["data"],
                },
                confidence_score=analysis["confidence_score"],
                sources=analysis["sources"],
                project_id=project.project_id,
            )
        if spec.agent_id == "agent-5":
            analysis = self.concept_provider.analyze(project.name, project.brief)
            return AgentOutput(
                agent_id=spec.agent_id,
                output_type="concept_generation_report",
                data={
                    "agent": asdict(spec),
                    "phase": project.current_phase.value,
                    "project_name": project.name,
                    "brief_excerpt": project.brief[:180],
                    **analysis["data"],
                },
                confidence_score=analysis["confidence_score"],
                sources=analysis["sources"],
                project_id=project.project_id,
            )
        if spec.agent_id == "agent-6":
            analysis = self.evaluation_provider.analyze(project.name, project.brief)
            return AgentOutput(
                agent_id=spec.agent_id,
                output_type="evaluation_report",
                data={
                    "agent": asdict(spec),
                    "phase": project.current_phase.value,
                    "project_name": project.name,
                    "brief_excerpt": project.brief[:180],
                    **analysis["data"],
                },
                confidence_score=analysis["confidence_score"],
                sources=analysis["sources"],
                project_id=project.project_id,
            )
        if spec.agent_id == "agent-8":
            analysis = self.gtm_provider.analyze(project.name, project.brief)
            return AgentOutput(
                agent_id=spec.agent_id,
                output_type="gtm_report",
                data={
                    "agent": asdict(spec),
                    "phase": project.current_phase.value,
                    "project_name": project.name,
                    "brief_excerpt": project.brief[:180],
                    **analysis["data"],
                },
                confidence_score=analysis["confidence_score"],
                sources=analysis["sources"],
                project_id=project.project_id,
            )
        if spec.agent_id == "agent-9":
            analysis = self.financial_provider.analyze(project.name, project.brief)
            return AgentOutput(
                agent_id=spec.agent_id,
                output_type="financial_report",
                data={
                    "agent": asdict(spec),
                    "phase": project.current_phase.value,
                    "project_name": project.name,
                    "brief_excerpt": project.brief[:180],
                    **analysis["data"],
                },
                confidence_score=analysis["confidence_score"],
                sources=analysis["sources"],
                project_id=project.project_id,
            )
        if spec.agent_id == "agent-10":
            analysis = self.risk_provider.analyze(project.name, project.brief)
            return AgentOutput(
                agent_id=spec.agent_id,
                output_type="risk_report",
                data={
                    "agent": asdict(spec),
                    "phase": project.current_phase.value,
                    "project_name": project.name,
                    "brief_excerpt": project.brief[:180],
                    **analysis["data"],
                },
                confidence_score=analysis["confidence_score"],
                sources=analysis["sources"],
                project_id=project.project_id,
            )
        if spec.agent_id == "agent-11":
            analysis = self.expansion_provider.analyze(project.name, project.brief)
            return AgentOutput(
                agent_id=spec.agent_id,
                output_type="expansion_report",
                data={
                    "agent": asdict(spec),
                    "phase": project.current_phase.value,
                    "project_name": project.name,
                    "brief_excerpt": project.brief[:180],
                    **analysis["data"],
                },
                confidence_score=analysis["confidence_score"],
                sources=analysis["sources"],
                project_id=project.project_id,
            )
        if spec.agent_id == "agent-12":
            analysis = self.synthesis_provider.analyze(project.name, project.brief)
            return AgentOutput(
                agent_id=spec.agent_id,
                output_type="synthesis_report",
                data={
                    "agent": asdict(spec),
                    "phase": project.current_phase.value,
                    "project_name": project.name,
                    "brief_excerpt": project.brief[:180],
                    **analysis["data"],
                },
                confidence_score=analysis["confidence_score"],
                sources=analysis["sources"],
                project_id=project.project_id,
            )

        phase_outputs = {
            DFNPhase.EMPATHIZE: {
                "summary": f"{spec.code_name} analyzed the project brief and produced baseline research findings.",
                "recommended_questions": [
                    "Which customer segment should be prioritized first?",
                    "What evidence will validate the market assumptions?",
                ],
            },
            DFNPhase.IDEATE: {
                "summary": f"{spec.code_name} generated structured strategic options for the selected opportunity space.",
                "recommended_questions": [
                    "Which concept direction best fits the target customer?",
                    "Which tradeoffs are acceptable for launch timing?",
                ],
            },
            DFNPhase.EVALUATE: {
                "summary": f"{spec.code_name} evaluated shortlisted concepts against desirability and feasibility criteria.",
                "recommended_questions": [
                    "Which concept deserves prototyping resources?",
                ],
            },
            DFNPhase.REALIZE: {
                "summary": f"{spec.code_name} translated approved concepts into launch and execution artifacts.",
                "recommended_questions": [
                    "Which realization dependency is most likely to block delivery?",
                ],
            },
            DFNPhase.MEASURE: {
                "summary": f"{spec.code_name} assembled post-decision intelligence and next-step recommendations.",
                "recommended_questions": [
                    "What should feed back into the next DFN cycle?",
                ],
            },
        }
        payload = {
            "agent": asdict(spec),
            "phase": project.current_phase.value,
            "project_name": project.name,
            "brief_excerpt": project.brief[:180],
            **phase_outputs[spec.phase],
        }
        return AgentOutput(
            agent_id=spec.agent_id,
            output_type=f"{spec.phase.value.lower()}_report",
            data=payload,
            confidence_score=0.62,
            sources=["human_project_brief", "stub_agent_runner"],
            project_id=project.project_id,
        )

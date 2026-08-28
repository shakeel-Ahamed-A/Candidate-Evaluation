from __future__ import annotations
from .models import AgentEvaluation, CandidateProfile, DebateRecord, Decision


def _directness(evaluation: AgentEvaluation) -> float:
    weights = {"interview": 1.0, "resume": 0.7, "job_description": 0.9}
    values = [weights[e.source.value] for finding in evaluation.findings for e in finding.evidence]
    return sum(values) / len(values) if values else 0.0


def decide(profile: CandidateProfile, independent: dict[str, AgentEvaluation], debate: DebateRecord, config: dict | None = None) -> Decision:
    cfg = config or {}
    weights = cfg.get("weights", {"technical": 1.0, "hr_culture": .9, "hiring_manager": 1.1, "skeptic": 1.0})
    critical = int(cfg.get("critical_concern_severity", 5))
    support = {}
    critical_findings = []
    role_findings = []
    for agent, evaluation in independent.items():
        value = evaluation.confidence * evaluation.evidence_quality * (.6 + .4 * _directness(evaluation)) * max(.25, evaluation.role_fit / 100) * weights.get(agent, 1.0)
        support[agent] = round(value, 3)
        for finding in evaluation.findings:
            if finding.type.value == "concern" and finding.severity >= critical:
                critical_findings.append((agent, finding))
            if finding.type.value == "concern" and finding.severity >= 4:
                role_findings.append((agent, finding))
    changed = [turn for group in debate.rounds for turn in group if turn.position_changed]
    disagreement = bool(debate.disagreement_summary)
    if critical_findings:
        recommendation = "more_info"
        escalation = [f"Critical finding from {agent}: {finding.title}" for agent, finding in critical_findings]
    elif role_findings and changed:
        recommendation = "more_info"
        escalation = ["A material role-relevant concern survived debate and triggered an opinion change."]
    elif disagreement and any(e.recommendation == "no_hire" for e in independent.values()):
        recommendation = "more_info"
        escalation = ["Material disagreement remains unresolved after the formal debate."]
    else:
        hire_strength = sum(support[a] for a, e in independent.items() if e.recommendation == "hire" and support[a] >= .30)
        no_hire_strength = sum(support[a] for a, e in independent.items() if e.recommendation == "no_hire" and support[a] >= .30)
        hire_count = sum(e.recommendation == "hire" and support[a] >= .30 for a, e in independent.items())
        no_hire_count = sum(e.recommendation == "no_hire" and support[a] >= .30 for a, e in independent.items())
        if hire_count >= 3 and hire_strength > no_hire_strength * 1.35:
            recommendation, escalation = "hire", []
        elif no_hire_count >= 2 and no_hire_strength > hire_strength * 1.25:
            recommendation, escalation = "no_hire", []
        else:
            recommendation, escalation = "more_info", ["Evidence did not clear a reliable acceptance/rejection threshold."]
    coverage = sum(e.evidence_quality * e.confidence for e in independent.values()) / max(1, len(independent))
    confidence = int(round(max(50, min(97, 100 * coverage * (0.93 - (.08 if changed else 0) - (.07 if disagreement else 0))))))
    unresolved = list(dict.fromkeys(debate.disagreement_summary))
    basis = [
        "Decision uses evidence quality, source directness, role fit, and non-linear decision gates rather than score averaging.",
        "Interview-sourced evidence is treated as more direct than resume-only assertions for disputed claims.",
        "Debate outcomes and opinion changes affect decision stability but do not replace source evidence.",
    ]
    if recommendation == "more_info":
        basis.append("More information is required because a material evidence gap or disagreement remains unresolved.")
    elif recommendation == "hire":
        basis.append("The acceptance gate is cleared without a critical unresolved contradiction.")
    else:
        basis.append("Material evidence gaps outweigh demonstrated role fit.")
    return Decision(
        recommendation=recommendation, confidence_percent=confidence, decision_basis=tuple(basis),
        evidence_hierarchy=("Direct interview evidence", "Corroborated facts", "Single-source resume claims", "Vague self-description"),
        weighted_support=tuple(support.items()), unresolved_disagreements=tuple(unresolved), escalation_reasons=tuple(escalation),
        role_fit=("Strong overall fit." if recommendation == "hire" else "Material gaps outweigh current evidence of fit." if recommendation == "no_hire" else "Promising but conditional on targeted validation."),
    )

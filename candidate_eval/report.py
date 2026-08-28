from __future__ import annotations
from datetime import datetime, timezone
from .models import EvaluationBundle, FindingType


def render_markdown(bundle: EvaluationBundle) -> str:
    d = bundle.decision
    lines = [f"# Candidate Evaluation Report - {bundle.profile.candidate_name}", "", f"**Target role:** {bundle.profile.role_target}", f"**Recommendation:** {d.recommendation.upper()}", f"**Confidence:** {d.confidence_percent}%", f"**Generated:** {datetime.now(timezone.utc).isoformat()}", "", "## Role fit", d.role_fit, "", "## Decision rationale"]
    lines += [f"- {x}" for x in d.decision_basis]
    lines += ["", "## Strengths"]
    strengths, concerns = [], []
    for agent, evaluation in bundle.independent_dict().items():
        for finding in evaluation.findings:
            quote = finding.evidence[0].quote
            if finding.type == FindingType.STRENGTH:
                strengths.append(f'- **{finding.title}** ({agent}; confidence {round(finding.confidence * 100)}%): {finding.statement} - evidence: "{quote}"')
            elif finding.type == FindingType.CONCERN:
                concerns.append(f'- **Severity {finding.severity}/5 - {finding.title}** ({agent}): {finding.statement} - evidence: "{quote}"')
    lines += strengths or ["- No strengths recorded."]
    lines += ["", "## Concerns"] + (concerns or ["- No concerns recorded."])
    lines += ["", "## Independent agent positions"]
    for agent, evaluation in bundle.independent_dict().items():
        lines.append(f"- **{agent}: {evaluation.recommendation.upper()}** - role fit {evaluation.role_fit}/100; confidence {round(evaluation.confidence*100)}%; evidence quality {round(evaluation.evidence_quality*100)}%.")
    lines += ["", "## Debate - explicit position changes"] + ([f"- {x}" for x in bundle.debate.changed_positions] or ["- None recorded."])
    lines += ["", "## Unresolved disagreements"] + ([f"- {x}" for x in d.unresolved_disagreements] or ["- None."])
    lines += ["", "## Evidence hierarchy"] + [f"{i+1}. {x}" for i, x in enumerate(d.evidence_hierarchy)]
    lines += ["", "## Debate transcript"]
    for round_no, turns in enumerate(bundle.debate.rounds, 1):
        lines += [f"### Round {round_no}"]
        for turn in turns:
            lines.append(f"- **{turn.speaker}**: {turn.argument}")
            if turn.responds_to:
                lines.append(f"  - Responds to: `{turn.responds_to}`")
            if turn.position_changed:
                lines.append(f"  - Position changed: `{turn.position_before}` -> `{turn.position_after}`")
                lines.append(f"  - Change reason: {turn.change_reason}")
            lines.append(f'  - Evidence: "{turn.evidence[0].quote}"')
    return "\n".join(lines) + "\n"

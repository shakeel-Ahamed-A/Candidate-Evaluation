from __future__ import annotations
from copy import deepcopy
from .llm import LLMBackend
from .models import AgentEvaluation, CandidateProfile
from .prompts import HIRING_MANAGER, HR_CULTURE, SKEPTIC, TECHNICAL

PERSONAS = {"technical": TECHNICAL, "hr_culture": HR_CULTURE, "hiring_manager": HIRING_MANAGER, "skeptic": SKEPTIC}


def evaluate_isolated(agent: str, profile: CandidateProfile, backend: LLMBackend) -> AgentEvaluation:
    if agent not in PERSONAS:
        raise ValueError(agent)
    isolated_profile = deepcopy(profile)
    payload = {"agent": agent, "profile": isolated_profile.model_dump(mode="json")}
    result = backend.structured(system=PERSONAS[agent], payload=payload, schema=AgentEvaluation)
    if result.agent != agent or not result.findings:
        raise RuntimeError("Independent agent response failed validation")
    finding_ids = {finding.finding_id for finding in result.findings}
    if not set(result.basis_finding_ids).issubset(finding_ids):
        raise RuntimeError("Agent recommendation references an unknown finding")
    source_text = profile.source_text_dict()
    for finding in result.findings:
        for evidence in finding.evidence:
            if evidence.quote not in source_text[evidence.source.value]:
                raise RuntimeError(f"Agent produced non-verbatim evidence: {evidence.quote!r}")
    return result

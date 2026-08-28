from __future__ import annotations
from typing import Type
from pydantic import BaseModel
from .models import AgentEvaluation, DebateTurn, EvidenceRef, Finding, FindingType, RoleExtraction, SourceType


def _source_lines(profile: dict, source: str) -> list[str]:
    for key, value in profile.get("source_text", []):
        if key == source:
            return [x.strip() for x in value.splitlines() if x.strip()]
    return []


def _evidence(payload: dict, *, keyword: str | None = None, source: str = "interview") -> EvidenceRef:
    profile = payload["profile"]
    lines = _source_lines(profile, source)
    line = next((x for x in lines if keyword and keyword.lower() in x.lower()), None) if keyword else None
    line = line or (lines[0] if lines else "No evidence")
    fact_id = "mock-evidence"
    for collection in ("claims", "skills", "experience", "education", "certifications", "metrics"):
        for item in profile.get(collection, []):
            for ref in item.get("evidence", []):
                if ref.get("quote") == line:
                    fact_id = ref.get("fact_id", fact_id)
                    break
    return EvidenceRef(source=SourceType(source), section="Source", quote=line, fact_id=fact_id)


def _has(payload: dict, phrase: str, source: str = "interview") -> bool:
    return any(phrase.lower() in line.lower() for line in _source_lines(payload["profile"], source))


def _candidate_a(payload: dict) -> bool:
    return "alex" in payload["profile"].get("candidate_name", "").lower()


def _technical_gap_evidence(payload: dict) -> EvidenceRef:
    return _evidence(payload, keyword="not designed") if _has(payload, "not designed") else _evidence(payload, keyword="designed")


def _role_mock(payload: dict) -> RoleExtraction:
    text = payload["role"]
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    title = next((x.split(":", 1)[1].strip() for x in lines if x.lower().startswith("role:")), "Target Role")
    summary = next((x.split(":", 1)[1].strip() for x in lines if x.lower().startswith("summary:")), "")
    def section(name, stops):
        raw = text.splitlines()
        start = next((i + 1 for i, line in enumerate(raw) if line.strip().lower() == name.lower()), None)
        if start is None: return []
        stopset = {x.lower() for x in stops}
        end = next((i for i in range(start, len(raw)) if raw[i].strip().lower() in stopset), len(raw))
        return [x.strip() for x in raw[start:end] if x.strip()]
    required = section("Required Skills", ("Preferred Skills", "Responsibilities", "Constraints"))
    preferred = section("Preferred Skills", ("Responsibilities", "Constraints"))
    responsibilities = section("Responsibilities", ("Constraints",))
    constraints = section("Constraints", ())
    evidence = []
    for heading, values in (("Required Skills", required), ("Preferred Skills", preferred), ("Responsibilities", responsibilities), ("Constraints", constraints)):
        for i, value in enumerate(values, 1):
            evidence.append(EvidenceRef(source=SourceType.JOB_DESCRIPTION, section=heading, quote=value, fact_id=f"role-{i}-{heading.lower().replace(' ', '-') }"))
    return RoleExtraction(title=title, summary=summary, required_skills=required, preferred_skills=preferred, responsibilities=responsibilities, constraints=constraints, evidence=evidence)


def generate_mock(*, schema: Type[BaseModel], system: str, payload: dict):
    strong = _candidate_a(payload)
    if schema is RoleExtraction:
        return _role_mock(payload)
    if schema is AgentEvaluation:
        agent = payload["agent"]
        ownership = _technical_gap_evidence(payload)
        impact = _evidence(payload, keyword="reduced") if _has(payload, "reduced") else _evidence(payload, keyword="save")
        behavior = _evidence(payload, keyword="outage") if _has(payload, "outage") else _evidence(payload, keyword="helped")
        if agent == "technical":
            if strong:
                findings = (
                    Finding(finding_id="technical-1", type=FindingType.STRENGTH, title="Relevant RTL implementation", statement="The candidate cites direct RTL/SystemVerilog implementation work relevant to the target role.", severity=1, evidence=(ownership,), confidence=.86),
                    Finding(finding_id="technical-2", type=FindingType.CONCERN, title="Architecture depth requires validation", statement="The architecture-ownership statement is stronger than the available design-detail evidence.", severity=4, evidence=(ownership,), confidence=.84),
                )
                return AgentEvaluation(agent=agent, role_fit=84, confidence=.86, recommendation="more_info", basis_finding_ids=("technical-1","technical-2"), findings=findings, key_risks=("Architecture depth",), evidence_quality=.88)
            findings = (
                Finding(finding_id="technical-1", type=FindingType.STRENGTH, title="Useful automation experience", statement="The candidate demonstrates practical Python automation and testing support.", severity=1, evidence=(behavior,), confidence=.76),
                Finding(finding_id="technical-2", type=FindingType.CONCERN, title="Production RTL gap", statement="The interview explicitly states that the candidate has not yet designed production RTL.", severity=3, evidence=(ownership,), confidence=.95),
            )
            return AgentEvaluation(agent=agent, role_fit=43, confidence=.88, recommendation="no_hire", basis_finding_ids=("technical-2",), findings=findings, key_risks=("No production RTL design evidence",), evidence_quality=.94)
        if agent == "hr_culture":
            if strong:
                findings = (
                    Finding(finding_id="hr-1", type=FindingType.STRENGTH, title="Accountability during failure", statement="The candidate describes an outage and the corrective action, showing direct ownership of a difficult event.", severity=1, evidence=(behavior,), confidence=.9),
                    Finding(finding_id="hr-2", type=FindingType.STRENGTH, title="Concrete communication", statement="The interview uses specific examples rather than abstract behavioral claims.", severity=1, evidence=(behavior,), confidence=.8),
                )
                return AgentEvaluation(agent=agent, role_fit=89, confidence=.85, recommendation="hire", basis_finding_ids=("hr-1","hr-2"), findings=findings, evidence_quality=.9)
            findings = (
                Finding(finding_id="hr-1", type=FindingType.STRENGTH, title="Team contribution", statement="The candidate gives a concrete example of helping the team automate recurring reporting work.", severity=1, evidence=(behavior,), confidence=.8),
                Finding(finding_id="hr-2", type=FindingType.NEUTRAL, title="Limited behavioral evidence", statement="The supplied interview contains only limited evidence for conflict-resolution or failure-handling behavior.", severity=2, evidence=(behavior,), confidence=.7),
            )
            return AgentEvaluation(agent=agent, role_fit=60, confidence=.78, recommendation="more_info", basis_finding_ids=("hr-1","hr-2"), findings=findings, evidence_quality=.82)
        if agent == "hiring_manager":
            if strong:
                return AgentEvaluation(agent=agent, role_fit=87, confidence=.84, recommendation="hire", basis_finding_ids=("hm-1","hm-2"), findings=(
                    Finding(finding_id="hm-1", type=FindingType.STRENGTH, title="Measurable engineering impact", statement="The candidate reports a measurable latency improvement relevant to system performance.", severity=1, evidence=(impact,), confidence=.81),
                    Finding(finding_id="hm-2", type=FindingType.CONCERN, title="Role-critical technical proof", statement="The target role needs independent architecture depth that is not fully established by the interview.", severity=4, evidence=(ownership,), confidence=.83),
                ), key_risks=("Technical validation",), evidence_quality=.87)
            return AgentEvaluation(agent=agent, role_fit=45, confidence=.87, recommendation="no_hire", basis_finding_ids=("hm-1","hm-2"), findings=(
                Finding(finding_id="hm-1", type=FindingType.CONCERN, title="Role-critical RTL requirement unmet", statement="The candidate acknowledges that production RTL design has not yet been performed.", severity=3, evidence=(ownership,), confidence=.96),
                Finding(finding_id="hm-2", type=FindingType.STRENGTH, title="Useful automation contribution", statement="The candidate reports saving the team two hours per week through automation.", severity=1, evidence=(behavior,), confidence=.84),
            ), key_risks=("Mismatch with core role requirement",), evidence_quality=.93)
        if strong:
            return AgentEvaluation(agent=agent, role_fit=66, confidence=.91, recommendation="more_info", basis_finding_ids=("skeptic-1","skeptic-2"), findings=(
                Finding(finding_id="skeptic-1", type=FindingType.CONCERN, title="Quantified claim lacks method", statement="The latency improvement is stated without enough measurement methodology or attribution detail.", severity=3, evidence=(impact,), confidence=.9),
                Finding(finding_id="skeptic-2", type=FindingType.CONCERN, title="Ownership language needs corroboration", statement="The architecture claim warrants direct verification because supporting detail is limited.", severity=3, evidence=(ownership,), confidence=.91),
            ), key_risks=("Unsupported claim",), evidence_quality=.92)
        return AgentEvaluation(agent=agent, role_fit=38, confidence=.9, recommendation="no_hire", basis_finding_ids=("skeptic-1",), findings=(
            Finding(finding_id="skeptic-1", type=FindingType.CONCERN, title="Core-skill evidence gap", statement="The candidate explicitly says production RTL has not yet been designed, while RTL is a required role skill.", severity=3, evidence=(ownership,), confidence=.97),
            Finding(finding_id="skeptic-2", type=FindingType.STRENGTH, title="Automation claim is concrete", statement="The reported two-hour weekly saving is a specific contribution rather than a vague statement.", severity=1, evidence=(behavior,), confidence=.82),
        ), key_risks=("Core-skill gap",), evidence_quality=.94)
    if schema is DebateTurn:
        r, s = payload["round_no"], payload["speaker"]
        strong = _candidate_a(payload)
        own = _technical_gap_evidence(payload)
        impact = _evidence(payload, keyword="reduced") if _has(payload, "reduced") else _evidence(payload, keyword="save")
        behavior = _evidence(payload, keyword="outage") if _has(payload, "outage") else _evidence(payload, keyword="helped")
        if strong:
            rows = {
                (1,"technical"):("skeptic",("skeptic-2",),"more_info","more_info","The implementation evidence is positive, but it still does not prove end-to-end architecture ownership.",own,False,None),
                (1,"skeptic"):("technical",("technical-1",),"more_info","more_info","Hands-on RTL work is useful evidence, but architecture ownership remains insufficiently corroborated.",own,False,None),
                (1,"hr_culture"):("skeptic",("skeptic-1",),"hire","hire","The quantified claim should be verified, but the interview also shows direct accountability during an outage.",behavior,False,None),
                (1,"hiring_manager"):("hr_culture",("hr-1",),"hire","hire","Behavioral evidence supports continued consideration while technical depth is clarified.",behavior,False,None),
                (2,"hiring_manager"):("technical",("technical-2",),"hire","more_info","Because architecture depth is central to the role, the unresolved evidence changes my decision threshold.",own,True,"The technical gap is directly tied to a role-critical requirement."),
                (2,"hr_culture"):("hiring_manager",("hm-2",),"hire","hire","I agree validation is needed, but accountability evidence remains favorable.",behavior,False,None),
                (2,"technical"):("hiring_manager",("hm-2",),"more_info","more_info","The role-specific requirement reinforces that a design-depth exercise is the right next step.",own,False,None),
                (2,"skeptic"):("technical",("technical-2",),"more_info","more_info","I agree the evidence gap is material without concluding that the claim is false.",impact,False,None),
                (3,"technical"):("hiring_manager",("hm-2",),"more_info","more_info","I retain MORE_INFO because direct design-depth validation is still missing.",own,False,None),
                (3,"skeptic"):("technical",("technical-2",),"more_info","more_info","The ownership and measurement questions remain unresolved, so rejection would be premature.",impact,False,None),
                (3,"hiring_manager"):("technical",("technical-2",),"more_info","more_info","I retain MORE_INFO because the technical gap remains role-critical.",own,False,None),
                (3,"hr_culture"):("hiring_manager",("hm-2",),"hire","hire","The behavioral evidence remains favorable while technical validation is outstanding.",behavior,False,None),
            }
        else:
            rows = {
                (1,"technical"):("skeptic",("skeptic-1",),"no_hire","no_hire","The absence of production RTL design is explicit and directly conflicts with a required role skill.",own,False,None),
                (1,"skeptic"):("technical",("technical-2",),"no_hire","no_hire","I agree the core-skill gap is decisive unless the role requirement is relaxed.",own,False,None),
                (1,"hr_culture"):("skeptic",("skeptic-1",),"more_info","more_info","The technical gap is real; I would want one more behavioral interview before a final rejection.",behavior,False,None),
                (1,"hiring_manager"):("hr_culture",("hr-1",),"no_hire","no_hire","The role's core RTL requirement is not met, despite useful automation experience.",own,False,None),
                (2,"hiring_manager"):("technical",("technical-2",),"no_hire","no_hire","The explicit lack of production RTL confirms the mismatch with the target role.",own,False,None),
                (2,"hr_culture"):("hiring_manager",("hm-1",),"more_info","no_hire","The role requirement is specific enough that I am moving from MORE_INFO to NO_HIRE.",own,True,"The hiring-manager finding tied the missing skill directly to a non-negotiable role requirement."),
                (2,"technical"):("hiring_manager",("hm-1",),"no_hire","no_hire","There is no evidence of production RTL design to offset the stated gap.",own,False,None),
                (2,"skeptic"):("technical",("technical-2",),"no_hire","no_hire","The explicit admission makes this a capability gap rather than an unverified claim.",own,False,None),
                (3,"technical"):("hiring_manager",("hm-1",),"no_hire","no_hire","My final position remains NO_HIRE because the core required skill is absent from the evidence.",own,False,None),
                (3,"skeptic"):("technical",("technical-2",),"no_hire","no_hire","The evidence is consistent across resume context and interview, so the concern remains unresolved in the candidate's favor.",own,False,None),
                (3,"hiring_manager"):("hr_culture",("hr-1",),"no_hire","no_hire","Useful automation does not substitute for the required production RTL capability.",behavior,False,None),
                (3,"hr_culture"):("hiring_manager",("hm-1",),"no_hire","no_hire","After considering the role requirement, I retain NO_HIRE.",own,False,None),
            }
        to, cited, before, after, argument, evidence, changed, reason = rows[(r,s)]
        return DebateTurn(round_no=r, speaker=s, responds_to=to, cited_findings=cited, position_before=before, position_after=after, argument=argument, evidence=(evidence,), position_changed=changed, change_reason=reason)
    raise ValueError(f"Mock backend does not support schema {schema}")

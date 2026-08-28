from __future__ import annotations

from enum import Enum
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class SourceType(str, Enum):
    RESUME = "resume"
    INTERVIEW = "interview"
    JOB_DESCRIPTION = "job_description"


class EvidenceRef(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source: SourceType
    section: str
    quote: str = Field(min_length=1)
    fact_id: str = Field(min_length=1)


class Skill(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str
    proficiency: Literal["novice", "working", "proficient", "advanced", "expert", "unknown"]
    years: float | None = None
    evidence: tuple[EvidenceRef, ...] = Field(default_factory=tuple)


class Experience(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    organization: str
    title: str
    start: str
    end: str | None = None
    responsibilities: tuple[str, ...] = Field(default_factory=tuple)
    achievements: tuple[str, ...] = Field(default_factory=tuple)
    evidence: tuple[EvidenceRef, ...] = Field(default_factory=tuple)


class Education(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    institution: str
    degree: str
    field: str | None = None
    year: int | None = None
    evidence: tuple[EvidenceRef, ...] = Field(default_factory=tuple)


class Claim(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    claim_id: str
    category: Literal["achievement", "capability", "ownership", "leadership", "impact", "other"]
    statement: str
    quantified_value: str | None = None
    evidence: tuple[EvidenceRef, ...] = Field(default_factory=tuple)


class Certification(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str
    issuer: str | None = None
    year: int | None = None
    evidence: tuple[EvidenceRef, ...] = Field(default_factory=tuple)


class Metric(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    metric_id: str
    value: str
    context: str
    evidence: tuple[EvidenceRef, ...] = Field(default_factory=tuple)


class RoleProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    title: str
    summary: str
    required_skills: tuple[str, ...] = Field(default_factory=tuple)
    preferred_skills: tuple[str, ...] = Field(default_factory=tuple)
    responsibilities: tuple[str, ...] = Field(default_factory=tuple)
    constraints: tuple[str, ...] = Field(default_factory=tuple)
    evidence: tuple[EvidenceRef, ...] = Field(default_factory=tuple)


class ProfileExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_name: str
    role_target: str
    skills: list[Skill] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)


class RoleExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    summary: str
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)


class CandidateProfile(BaseModel):
    """Frozen, content-addressed shared context for the independent agents."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    profile_id: str
    candidate_name: str
    role_target: str
    role_profile: RoleProfile
    source_hashes: tuple[tuple[SourceType, str], ...]
    source_lengths: tuple[tuple[SourceType, int], ...]
    source_text: tuple[tuple[SourceType, str], ...]
    skills: tuple[Skill, ...] = Field(default_factory=tuple)
    experience: tuple[Experience, ...] = Field(default_factory=tuple)
    education: tuple[Education, ...] = Field(default_factory=tuple)
    claims: tuple[Claim, ...] = Field(default_factory=tuple)
    certifications: tuple[Certification, ...] = Field(default_factory=tuple)
    metrics: tuple[Metric, ...] = Field(default_factory=tuple)

    def source_text_dict(self) -> dict[str, str]:
        return {source.value if isinstance(source, SourceType) else str(source): text for source, text in self.source_text}

class FindingType(str, Enum):
    STRENGTH = "strength"
    CONCERN = "concern"
    NEUTRAL = "neutral"


class Finding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    finding_id: str
    type: FindingType
    title: str
    statement: str
    severity: int = Field(ge=1, le=5)
    evidence: tuple[EvidenceRef, ...] = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


class AgentEvaluation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    agent: str
    role_fit: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    recommendation: Literal["hire", "no_hire", "more_info"]
    basis_finding_ids: tuple[str, ...] = Field(min_length=1)
    findings: tuple[Finding, ...] = Field(min_length=1)
    key_risks: tuple[str, ...] = Field(default_factory=tuple)
    evidence_quality: float = Field(ge=0, le=1)


class DebateTurn(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    round_no: int = Field(ge=1)
    speaker: str
    responds_to: str | None = None
    cited_findings: tuple[str, ...] = Field(default_factory=tuple)
    position_before: Literal["hire", "no_hire", "more_info"]
    position_after: Literal["hire", "no_hire", "more_info"]
    argument: str
    evidence: tuple[EvidenceRef, ...] = Field(min_length=1)
    position_changed: bool = False
    change_reason: str | None = None


class DebateRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    rounds: tuple[tuple[DebateTurn, ...], ...] = Field(min_length=3)
    disagreement_summary: tuple[str, ...] = Field(default_factory=tuple)
    changed_positions: tuple[str, ...] = Field(default_factory=tuple)


class Decision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    recommendation: Literal["hire", "no_hire", "more_info"]
    confidence_percent: int = Field(ge=0, le=100)
    decision_basis: tuple[str, ...] = Field(min_length=1)
    evidence_hierarchy: tuple[str, ...] = Field(min_length=1)
    weighted_support: tuple[tuple[str, float], ...]
    unresolved_disagreements: tuple[str, ...] = Field(default_factory=tuple)
    escalation_reasons: tuple[str, ...] = Field(default_factory=tuple)
    role_fit: str


class EvaluationBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile: CandidateProfile
    independent: tuple[tuple[str, AgentEvaluation], ...]
    debate: DebateRecord
    decision: Decision

    def independent_dict(self) -> dict[str, AgentEvaluation]:
        return dict(self.independent)

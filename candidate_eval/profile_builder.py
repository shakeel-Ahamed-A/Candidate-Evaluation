from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .models import CandidateProfile, Certification, Claim, Education, EvidenceRef, Experience, Metric, ProfileExtraction, RoleExtraction, RoleProfile, Skill, SourceType


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _evidence(source: SourceType, section: str, quote: str, fact_id: str) -> EvidenceRef:
    return EvidenceRef(source=source, section=section, quote=quote.strip(), fact_id=fact_id)


def _lines(text: str) -> list[str]:
    return [x.strip() for x in text.splitlines() if x.strip()]


def _first_non_heading_line(text: str) -> str:
    headings = {"resume", "curriculum vitae", "cv"}
    for line in _lines(text):
        if line.lower() not in headings:
            return line
    return "Unknown Candidate"


def _section(text: str, heading: str, stop_headings: tuple[str, ...]) -> list[str]:
    lines = text.splitlines()
    start = next((i + 1 for i, line in enumerate(lines) if line.strip().lower() == heading.lower()), None)
    if start is None:
        return []
    stops = {x.lower() for x in stop_headings}
    end = next((i for i in range(start, len(lines)) if lines[i].strip().lower() in stops), len(lines))
    return [x.strip() for x in lines[start:end] if x.strip()]


def _role_profile(role_text: str) -> RoleProfile:
    lines = _lines(role_text)
    title = next((x.split(":", 1)[1].strip() for x in lines if x.lower().startswith("role:")), "Target Role")
    summary = next((x.split(":", 1)[1].strip() for x in lines if x.lower().startswith("summary:")), "")
    required = _section(role_text, "Required Skills", ("Preferred Skills", "Responsibilities", "Constraints"))
    preferred = _section(role_text, "Preferred Skills", ("Responsibilities", "Constraints"))
    responsibilities = _section(role_text, "Responsibilities", ("Constraints",))
    constraints = _section(role_text, "Constraints", ())
    refs: list[EvidenceRef] = []
    for heading, values in (("Required Skills", required), ("Preferred Skills", preferred), ("Responsibilities", responsibilities), ("Constraints", constraints)):
        for i, value in enumerate(values, 1):
            refs.append(_evidence(SourceType.JOB_DESCRIPTION, heading, value, f"role-{heading.lower().replace(' ', '-')}-{i}"))
    return RoleProfile(title=title, summary=summary, required_skills=tuple(required), preferred_skills=tuple(preferred), responsibilities=tuple(responsibilities), constraints=tuple(constraints), evidence=tuple(refs))


def _skill_candidates(*texts: str) -> list[str]:
    catalog = ["Python", "Verilog", "SystemVerilog", "MATLAB", "LTspice", "SQL", "Docker", "Kubernetes", "Git", "C++", "C", "Java", "React", "AWS", "Azure", "GCP", "Linux", "Jenkins", "Prometheus", "Grafana", "PostgreSQL", "REST APIs", "System Design", "RTL", "CI/CD"]
    haystack = "\n".join(texts)
    return [skill for skill in catalog if re.search(rf"(?<!\w){re.escape(skill)}(?!\w)", haystack, re.I)]


def _skill_level(skill: str, resume_text: str) -> str:
    match = re.search(rf"{re.escape(skill)}\s*[:\-]\s*(novice|working|proficient|advanced|expert)", resume_text, re.I)
    return match.group(1).lower() if match else "unknown"


def _claims_and_metrics(interview_text: str) -> tuple[list[Claim], list[Metric]]:
    claims: list[Claim] = []
    metrics: list[Metric] = []
    sentences = re.split(r"(?<=[.!?])\s+|\n+", interview_text)
    claim_no = metric_no = 1
    metric_pattern = r"\d+(?:\.\d+)?\s*(?:%|ms|s|days?|years?|teams?|users?|dollars?|k|m)\b"
    for sentence in (x.strip() for x in sentences if x.strip()):
        low = sentence.lower()
        category = None
        if re.search(r"\bi (?:reduced|increased|improved|delivered|saved|cut)\b", low):
            category = "impact"
        elif re.search(r"\bi (?:designed|architected|built|implemented|owned)\b", low):
            category = "ownership"
        elif re.search(r"\bi (?:led|managed|mentored|coordinated)\b", low):
            category = "leadership"
        elif re.search(r"\bi am (?:experienced|advanced|expert|proficient)\b", low):
            category = "capability"
        quantified = re.search(metric_pattern, sentence, re.I)
        if category:
            fact_id = f"claim-{claim_no}"
            claims.append(Claim(claim_id=fact_id, category=category, statement=sentence, quantified_value=quantified.group(0) if quantified else None, evidence=(_evidence(SourceType.INTERVIEW, "Interview", sentence, fact_id),)))
            claim_no += 1
        for match in re.finditer(metric_pattern, sentence, re.I):
            fact_id = f"metric-{metric_no}"
            metrics.append(Metric(metric_id=fact_id, value=match.group(0), context=sentence, evidence=(_evidence(SourceType.INTERVIEW, "Interview", sentence, fact_id),)))
            metric_no += 1
    return claims, metrics


def _build(resume_text: str, interview_text: str, role_text: str) -> CandidateProfile:
    role = _role_profile(role_text)
    skills = []
    for i, skill in enumerate(_skill_candidates(resume_text, interview_text), 1):
        line = next((x.strip() for x in resume_text.splitlines() if re.search(rf"(?<!\w){re.escape(skill)}(?!\w)", x, re.I)), skill)
        skills.append(Skill(name=skill, proficiency=_skill_level(skill, resume_text), evidence=(_evidence(SourceType.RESUME, "Skills", line, f"skill-{i}"),)))
    experience = []
    for i, line in enumerate(_section(resume_text, "Experience", ("Education", "Certifications", "Skills")), 1):
        parts = [x.strip() for x in line.split("|")]
        if len(parts) >= 3:
            experience.append(Experience(organization=parts[0], title=parts[1], start=parts[2], end=parts[3] if len(parts) > 3 else None, evidence=(_evidence(SourceType.RESUME, "Experience", line, f"exp-{i}"),)))
    education = []
    for i, line in enumerate(_section(resume_text, "Education", ("Certifications", "Skills", "Experience")), 1):
        parts = [x.strip() for x in line.split("|")]
        if len(parts) >= 2:
            year = int(parts[3]) if len(parts) >= 4 and parts[3].isdigit() else None
            education.append(Education(institution=parts[0], degree=parts[1], field=parts[2] if len(parts) >= 3 else None, year=year, evidence=(_evidence(SourceType.RESUME, "Education", line, f"edu-{i}"),)))
    certifications = []
    for i, line in enumerate(_section(resume_text, "Certifications", ("Skills", "Experience", "Education")), 1):
        year_match = re.search(r"\b(20\d{2})\b", line)
        base = re.sub(r"\(20\d{2}\)", "", line).strip()
        issuer = None
        if " - " in base:
            base, issuer = [x.strip() for x in base.split(" - ", 1)]
        certifications.append(Certification(name=base, issuer=issuer, year=int(year_match.group(1)) if year_match else None, evidence=(_evidence(SourceType.RESUME, "Certifications", line, f"cert-{i}"),)))
    claims, metrics = _claims_and_metrics(interview_text)
    canonical = f"RESUME\n{resume_text}\nINTERVIEW\n{interview_text}\nJOB\n{role_text}"
    return CandidateProfile(
        profile_id=f"profile-{sha256_text(canonical)[:20]}",
        candidate_name=_first_non_heading_line(resume_text),
        role_target=role.title,
        role_profile=role,
        source_hashes=((SourceType.RESUME, sha256_text(resume_text)), (SourceType.INTERVIEW, sha256_text(interview_text)), (SourceType.JOB_DESCRIPTION, sha256_text(role_text))),
        source_lengths=((SourceType.RESUME, len(resume_text)), (SourceType.INTERVIEW, len(interview_text)), (SourceType.JOB_DESCRIPTION, len(role_text))),
        source_text=((SourceType.RESUME, resume_text), (SourceType.INTERVIEW, interview_text), (SourceType.JOB_DESCRIPTION, role_text)),
        skills=tuple(skills), experience=tuple(experience), education=tuple(education), claims=tuple(claims), certifications=tuple(certifications), metrics=tuple(metrics),
    )


def build_profile(resume_text: str, interview_text: str, role_text: str) -> CandidateProfile:
    return _build(resume_text, interview_text, role_text)


def _validate_extracted_evidence(extracted: ProfileExtraction, resume_text: str, interview_text: str) -> None:
    sources = {SourceType.RESUME: resume_text, SourceType.INTERVIEW: interview_text}
    for collection in (extracted.skills, extracted.experience, extracted.education, extracted.claims, extracted.certifications, extracted.metrics):
        for item in collection:
            if not item.evidence:
                raise ValueError("Every extracted fact must contain evidence")
            for evidence in item.evidence:
                if evidence.quote not in sources[evidence.source]:
                    raise ValueError(f"Non-verbatim evidence returned by extractor: {evidence.quote!r}")


EXTRACTION_PROMPT = """
Extract only factual information from the candidate resume and interview transcript. Preserve dates,
responsibilities, achievements, skills, certifications, candidate claims and meaningful metrics.
Every extracted candidate fact must have one or more EvidenceRef entries with exact verbatim quotes.
Do not infer missing proficiency. Distinguish candidate claims from independently corroborated facts.
"""

ROLE_EXTRACTION_PROMPT = """
Extract the job description into a factual role profile. Preserve the exact role title, summary, required skills,
preferred skills, responsibilities, and constraints. Every extracted role item must cite a verbatim EvidenceRef
from the job description. Do not introduce requirements that are not stated.
"""


def build_profile_with_backend(resume_text: str, interview_text: str, role_text: str, backend) -> CandidateProfile:
    extracted: ProfileExtraction = backend.structured(system=EXTRACTION_PROMPT, payload={"resume": resume_text, "interview": interview_text, "role": role_text}, schema=ProfileExtraction)
    _validate_extracted_evidence(extracted, resume_text, interview_text)
    role_extracted: RoleExtraction = backend.structured(system=ROLE_EXTRACTION_PROMPT, payload={"role": role_text}, schema=RoleExtraction)
    for evidence in role_extracted.evidence:
        if evidence.source != SourceType.JOB_DESCRIPTION or evidence.quote not in role_text:
            raise ValueError(f"Role extractor produced invalid evidence: {evidence.quote!r}")
    role = RoleProfile(title=role_extracted.title, summary=role_extracted.summary, required_skills=tuple(role_extracted.required_skills), preferred_skills=tuple(role_extracted.preferred_skills), responsibilities=tuple(role_extracted.responsibilities), constraints=tuple(role_extracted.constraints), evidence=tuple(role_extracted.evidence))
    canonical = f"RESUME\n{resume_text}\nINTERVIEW\n{interview_text}\nJOB\n{role_text}"
    return CandidateProfile(
        profile_id=f"profile-{sha256_text(canonical)[:20]}", candidate_name=extracted.candidate_name, role_target=role.title,
        role_profile=role,
        source_hashes=((SourceType.RESUME, sha256_text(resume_text)), (SourceType.INTERVIEW, sha256_text(interview_text)), (SourceType.JOB_DESCRIPTION, sha256_text(role_text))),
        source_lengths=((SourceType.RESUME, len(resume_text)), (SourceType.INTERVIEW, len(interview_text)), (SourceType.JOB_DESCRIPTION, len(role_text))),
        source_text=((SourceType.RESUME, resume_text), (SourceType.INTERVIEW, interview_text), (SourceType.JOB_DESCRIPTION, role_text)),
        skills=tuple(extracted.skills), experience=tuple(extracted.experience), education=tuple(extracted.education), claims=tuple(extracted.claims), certifications=tuple(extracted.certifications), metrics=tuple(extracted.metrics),
    )


def persist_profile(profile: CandidateProfile, out: Path) -> str:
    out.parent.mkdir(parents=True, exist_ok=True)
    canonical = json.dumps(profile.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    sidecar = out.with_suffix(out.suffix + ".sha256")
    if out.exists():
        if not sidecar.exists():
            raise FileExistsError(f"Immutable profile exists without sidecar: {out}")
        existing = sidecar.read_text(encoding="utf-8").strip()
        if existing != digest:
            raise FileExistsError(f"Immutable profile exists with different content: {out}")
        return digest
    out.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
    sidecar.write_text(digest, encoding="utf-8")
    return digest


def verify_profile(profile: CandidateProfile, expected_digest: str) -> None:
    canonical = json.dumps(profile.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if digest != expected_digest:
        raise RuntimeError("Candidate profile integrity check failed")

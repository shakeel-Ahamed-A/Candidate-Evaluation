from __future__ import annotations
import json
from pathlib import Path
from .agents import PERSONAS, evaluate_isolated
from .debate import run_debate
from .decision import decide
from .ingestion import load_document
from .llm import make_backend
from .models import EvaluationBundle
from .profile_builder import build_profile, build_profile_with_backend, persist_profile, verify_profile
from .report import render_markdown


def _safe_name(name: str) -> str:
    clean = "".join(c if c.isalnum() or c in "-_" else "_" for c in name.strip())
    return clean.strip("_") or "candidate"


def run_candidate(resume_path: Path, interview_path: Path, job_path: Path, config: dict, out_dir: Path) -> EvaluationBundle:
    backend = make_backend(config.get("provider", "mock"), config.get("model"))
    resume, interview, job = load_document(resume_path), load_document(interview_path), load_document(job_path)
    profile = build_profile(resume, interview, job) if config.get("provider") == "mock" else build_profile_with_backend(resume, interview, job, backend)
    candidate_dir = out_dir / _safe_name(profile.candidate_name)
    candidate_dir.mkdir(parents=True, exist_ok=True)
    profile_path = candidate_dir / f"{profile.profile_id}.json"
    digest = persist_profile(profile, profile_path)
    verify_profile(profile, digest)
    independent = {}
    for agent_name in PERSONAS:
        verify_profile(profile, digest)
        independent[agent_name] = evaluate_isolated(agent_name, profile, backend)
        verify_profile(profile, digest)
    debate = run_debate(profile, independent, backend)
    decision = decide(profile, independent, debate, config)
    bundle = EvaluationBundle(profile=profile, independent=tuple(independent.items()), debate=debate, decision=decision)
    (candidate_dir / "evaluation_bundle.json").write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    (candidate_dir / "report.md").write_text(render_markdown(bundle), encoding="utf-8")
    return bundle


def run_batch(job_path: Path, candidate_paths: dict[str, tuple[Path, Path]], config: dict, out_dir: Path) -> dict[str, EvaluationBundle]:
    if len(candidate_paths) < 2:
        raise ValueError("The instructor's problem statement requires both candidates to be processed")
    load_document(job_path)
    results = {}
    for label, (resume_path, interview_path) in candidate_paths.items():
        results[label] = run_candidate(resume_path, interview_path, job_path, config, out_dir)
    manifest = {"job_description": str(job_path), "candidates": {}}
    for label, bundle in results.items():
        candidate_dir = out_dir / _safe_name(bundle.profile.candidate_name)
        manifest["candidates"][label] = {
            "candidate_name": bundle.profile.candidate_name,
            "recommendation": bundle.decision.recommendation,
            "confidence_percent": bundle.decision.confidence_percent,
            "report": str(candidate_dir / "report.md"),
            "evaluation_bundle": str(candidate_dir / "evaluation_bundle.json"),
        }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "batch_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return results

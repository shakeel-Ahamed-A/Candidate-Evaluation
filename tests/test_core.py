from pathlib import Path
import json
import pytest
from candidate_eval.agents import evaluate_isolated, PERSONAS
from candidate_eval.batch import discover_candidates
from candidate_eval.debate import run_debate
from candidate_eval.ingestion import load_document
from candidate_eval.llm import MockBackend
from candidate_eval.orchestrator import run_batch
from candidate_eval.profile_builder import build_profile, persist_profile, verify_profile

ROOT = Path(__file__).parents[1]


def make_profile(label="A"):
    job, candidates = discover_candidates(ROOT / "sample")
    resume, transcript = candidates[label]
    return build_profile(load_document(resume), load_document(transcript), load_document(job))


def test_pdf_ingestion_and_both_candidate_discovery():
    job, candidates = discover_candidates(ROOT / "sample")
    assert job.suffix == ".pdf"
    assert set(candidates) == {"A", "B"}
    assert "Alex Menon" in load_document(candidates["A"][0])
    assert "Priya Shah" in load_document(candidates["B"][0])


def test_profile_is_deeply_immutable():
    p = make_profile()
    with pytest.raises((TypeError, ValueError)):
        p.role_target = "Changed"
    with pytest.raises((AttributeError, TypeError)):
        p.skills.append("x")
    with pytest.raises((TypeError, ValueError)):
        p.source_text += (("fake", "data"),)
    with pytest.raises((TypeError, ValueError)):
        p.role_profile.required_skills += ("fake",)


def test_profile_hash_roundtrip(tmp_path):
    p = make_profile()
    path = tmp_path / "profile.json"
    digest = persist_profile(p, path)
    verify_profile(p, digest)
    assert json.loads(path.read_text())["candidate_name"] == p.candidate_name


def test_each_persona_is_independent_and_evidence_grounded():
    p = make_profile()
    for agent in PERSONAS:
        result = evaluate_isolated(agent, p, MockBackend())
        assert result.agent == agent
        assert result.findings
        assert all(f.evidence for f in result.findings)


def test_debate_protocol():
    p = make_profile()
    independent = {agent: evaluate_isolated(agent, p, MockBackend()) for agent in PERSONAS}
    debate = run_debate(p, independent, MockBackend())
    assert len(debate.rounds) == 3
    all_turns = [turn for group in debate.rounds for turn in group]
    assert any(turn.responds_to for turn in all_turns)
    assert any(turn.position_changed for turn in all_turns)
    assert all(turn.change_reason for turn in all_turns if turn.position_changed)


def test_batch_end_to_end_processes_both_candidates(tmp_path):
    job, candidates = discover_candidates(ROOT / "sample")
    cfg = {
        "provider": "mock", "model": "gpt-5.6", "critical_concern_severity": 5,
        "weights": {"technical": 1.0, "hr_culture": .9, "hiring_manager": 1.1, "skeptic": 1.0}
    }
    result = run_batch(job, candidates, cfg, tmp_path)
    assert set(result) == {"A", "B"}
    assert result["A"].decision.recommendation == "more_info"
    assert result["B"].decision.recommendation == "no_hire"
    assert (tmp_path / "batch_manifest.json").exists()

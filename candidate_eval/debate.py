from __future__ import annotations
from .llm import LLMBackend
from .models import AgentEvaluation, CandidateProfile, DebateRecord, DebateTurn
from .prompts import DEBATE


def validate_no_reasoning_leak(payload: dict) -> None:
    forbidden = ("reasoning_trace", "chain_of_thought", "private_reasoning")
    if any(token in str(payload).lower() for token in forbidden):
        raise RuntimeError("Debate payload contains forbidden reasoning-trace material")


def run_debate(profile: CandidateProfile, independent: dict[str, AgentEvaluation], backend: LLMBackend) -> DebateRecord:
    locked = {name: evaluation.model_dump(mode="json") for name, evaluation in independent.items()}
    transcript: list[dict] = []
    rounds: list[list[DebateTurn]] = []
    schedules = [
        ["technical", "skeptic", "hr_culture", "hiring_manager"],
        ["hiring_manager", "hr_culture", "technical", "skeptic"],
        ["technical", "skeptic", "hiring_manager", "hr_culture"],
    ]
    for round_no, speakers in enumerate(schedules, 1):
        current: list[DebateTurn] = []
        for speaker in speakers:
            payload = {"profile": profile.model_dump(mode="json"), "locked_independent_evaluations": locked, "prior_debate_transcript": transcript, "speaker": speaker, "round_no": round_no}
            validate_no_reasoning_leak(payload)
            turn = backend.structured(system=DEBATE, payload=payload, schema=DebateTurn)
            if not isinstance(turn, DebateTurn) or turn.round_no != round_no or turn.speaker != speaker or not turn.evidence:
                raise RuntimeError("Invalid debate turn")
            profile_sources = profile.source_text_dict()
            for evidence in turn.evidence:
                if evidence.quote not in profile_sources[evidence.source.value]:
                    raise RuntimeError(f"Debate produced non-verbatim evidence: {evidence.quote!r}")
            if turn.cited_findings and not any(turn.cited_findings):
                raise RuntimeError("Debate cited-finding list is invalid")
            if turn.position_changed and not turn.change_reason:
                raise RuntimeError("Every opinion change must state a reason")
            current.append(turn)
            transcript.append(turn.model_dump(mode="json"))
        rounds.append(current)
    all_turns = [turn for group in rounds for turn in group]
    if len(rounds) < 3 or not any(turn.responds_to for turn in all_turns) or not any(turn.position_changed for turn in all_turns):
        raise RuntimeError("Debate protocol requires >=3 rounds, direct response, and an opinion change")
    final_positions = {turn.speaker: turn.position_after for turn in all_turns if turn.round_no == 3}
    disagreements = []
    if len(set(final_positions.values())) > 1:
        disagreements.append("Final debate positions remained divergent: " + ", ".join(f"{agent}={position}" for agent, position in sorted(final_positions.items())) + ".")
    changes = [f"{turn.speaker}: {turn.position_before} -> {turn.position_after}; reason: {turn.change_reason}" for turn in all_turns if turn.position_changed]
    return DebateRecord(rounds=rounds, disagreement_summary=list(dict.fromkeys(disagreements)), changed_positions=changes)

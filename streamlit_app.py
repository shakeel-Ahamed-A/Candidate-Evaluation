from __future__ import annotations

import json
import tempfile
from pathlib import Path

import streamlit as st

from candidate_eval.batch import discover_candidates
from candidate_eval.orchestrator import run_batch


# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="Multi-Agent AI Interview Panel",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------
# Styling
# ---------------------------------------------------------

st.markdown(
    """
    <style>
        .main-title {
            font-size: 2.4rem;
            font-weight: 750;
            margin-bottom: 0.2rem;
        }

        .subtitle {
            font-size: 1.05rem;
            color: #64748b;
            margin-bottom: 1.5rem;
        }

        .decision-card {
            padding: 1rem 1.2rem;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            background: #f8fafc;
            margin-bottom: 1rem;
        }

        .section-title {
            font-size: 1.35rem;
            font-weight: 700;
            margin-top: 1rem;
        }

        .finding-card {
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 0.8rem 1rem;
            margin-bottom: 0.7rem;
            background: white;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def save_uploaded_file(uploaded_file, destination: Path) -> Path:
    """Save an uploaded Streamlit file to disk."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(uploaded_file.getbuffer())
    return destination


def recommendation_label(value: str) -> str:
    """Convert internal recommendation value to readable text."""
    return {
        "hire": "HIRE",
        "no_hire": "NO HIRE",
        "more_info": "MORE INFO",
    }.get(value.lower(), value.upper())


def recommendation_icon(value: str) -> str:
    return {
        "hire": "✅",
        "no_hire": "❌",
        "more_info": "⚠️",
    }.get(value.lower(), "ℹ️")


def render_finding(finding) -> None:
    """Render one evidence-backed agent finding."""
    st.markdown(
        f"""
        <div class="finding-card">
            <b>{finding.title}</b><br>
            {finding.statement}<br><br>
            <b>Severity:</b> {finding.severity}/5
            &nbsp;&nbsp;
            <b>Confidence:</b> {finding.confidence:.0%}
        </div>
        """,
        unsafe_allow_html=True,
    )

    for evidence in finding.evidence:
        source = evidence.source.value
        st.caption(
            f'📌 {source} | {evidence.section}: "{evidence.quote}"'
        )


def render_agent_evaluation(agent_name: str, evaluation) -> None:
    """Render a complete independent agent evaluation."""
    st.subheader(agent_name)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Role Fit", f"{evaluation.role_fit}/100")

    with col2:
        st.metric("Confidence", f"{evaluation.confidence:.0%}")

    with col3:
        st.metric(
            "Recommendation",
            recommendation_label(evaluation.recommendation),
        )

    st.caption(
        f"Evidence quality: {evaluation.evidence_quality:.0%}"
    )

    for finding in evaluation.findings:
        render_finding(finding)


def render_debate(debate) -> None:
    """Render the multi-round debate."""
    st.markdown(
        '<div class="section-title">Structured Debate</div>',
        unsafe_allow_html=True,
    )

    for round_turns in debate.rounds:
        round_no = round_turns[0].round_no

        with st.expander(f"Round {round_no}", expanded=True):
            for turn in round_turns:
                changed = " 🔄 Position changed" if turn.position_changed else ""

                st.markdown(
                    f"**{turn.speaker}**{changed}"
                )

                st.write(turn.argument)

                st.caption(
                    f"Position: "
                    f"{turn.position_before.upper()} → "
                    f"{turn.position_after.upper()}"
                )

                if turn.responds_to:
                    st.caption(
                        f"Responds to: {turn.responds_to}"
                    )

                if turn.change_reason:
                    st.info(
                        f"Why the position changed: {turn.change_reason}"
                    )

                for evidence in turn.evidence:
                    st.caption(
                        f'📌 {evidence.source.value} | '
                        f'{evidence.section}: "{evidence.quote}"'
                    )

    if debate.disagreement_summary:
        st.subheader("Unresolved Disagreements")

        for disagreement in debate.disagreement_summary:
            st.warning(disagreement)


def render_decision(decision) -> None:
    """Render final non-averaged decision."""
    icon = recommendation_icon(decision.recommendation)

    st.markdown(
        f"""
        <div class="decision-card">
            <h2>{icon} {recommendation_label(decision.recommendation)}</h2>
            <h3>Confidence: {decision.confidence_percent}%</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Decision Basis")

    for item in decision.decision_basis:
        st.markdown(f"- {item}")

    st.subheader("Role Fit")

    st.write(decision.role_fit)

    st.subheader("Evidence Hierarchy")

    for item in decision.evidence_hierarchy:
        st.markdown(f"- {item}")

    if decision.escalation_reasons:
        st.subheader("Escalation Reasons")

        for reason in decision.escalation_reasons:
            st.warning(reason)


def render_candidate(bundle, label: str) -> None:
    """Render all results for one candidate."""

    profile = bundle.profile
    decision = bundle.decision

    st.markdown(
        f'<div class="section-title">Candidate {label}: '
        f'{profile.candidate_name}</div>',
        unsafe_allow_html=True,
    )

    # High-level result
    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Recommendation",
            recommendation_label(decision.recommendation),
        )

    with c2:
        st.metric(
            "Confidence",
            f"{decision.confidence_percent}%",
        )

    with c3:
        st.metric(
            "Role",
            profile.role_target,
        )

    # Profile
    with st.expander("Candidate Profile", expanded=False):
        st.write("### Skills")

        for skill in profile.skills:
            years = (
                f" — {skill.years} years"
                if skill.years is not None
                else ""
            )

            st.write(
                f"**{skill.name}** — "
                f"{skill.proficiency}{years}"
            )

        st.write("### Experience")

        for experience in profile.experience:
            st.write(
                f"**{experience.title} — "
                f"{experience.organization}** "
                f"({experience.start} → {experience.end or 'Present'})"
            )

            for achievement in experience.achievements:
                st.write(f"- {achievement}")

        if profile.education:
            st.write("### Education")

            for education in profile.education:
                st.write(
                    f"**{education.degree}** — "
                    f"{education.institution}"
                )

        if profile.certifications:
            st.write("### Certifications")

            for certification in profile.certifications:
                issuer = (
                    f" ({certification.issuer})"
                    if certification.issuer
                    else ""
                )

                st.write(
                    f"- {certification.name}{issuer}"
                )

        if profile.metrics:
            st.write("### Metrics")

            for metric in profile.metrics:
                st.write(
                    f"- **{metric.context}:** {metric.value}"
                )

    # Independent evaluations
    st.subheader("Independent Agent Evaluations")

    evaluations = bundle.independent_dict()

    tabs = st.tabs(
        [
            "Technical",
            "HR / Culture",
            "Hiring Manager",
            "Skeptic",
        ]
    )

    agent_order = [
        "technical",
        "hr_culture",
        "hiring_manager",
        "skeptic",
    ]

    for tab, agent_name in zip(tabs, agent_order):
        with tab:
            evaluation = evaluations.get(agent_name)

            if evaluation is None:
                st.error(
                    f"Evaluation missing for {agent_name}."
                )
            else:
                render_agent_evaluation(
                    agent_name.replace("_", " ").title(),
                    evaluation,
                )

    # Debate
    render_debate(bundle.debate)

    # Final decision
    st.markdown("---")

    st.markdown(
        '<div class="section-title">Final Decision</div>',
        unsafe_allow_html=True,
    )

    render_decision(decision)

    # Raw JSON
    with st.expander("Raw Evaluation JSON", expanded=False):
        st.json(
            json.loads(bundle.model_dump_json())
        )


# ---------------------------------------------------------
# Header
# ---------------------------------------------------------

st.markdown(
    '<div class="main-title">🤖 Multi-Agent AI Interview Panel Simulator</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="subtitle">
    Four isolated AI personas independently evaluate candidates,
    debate evidence, and produce an explainable hiring decision.
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------

st.sidebar.header("Evaluation Settings")

provider = st.sidebar.selectbox(
    "AI Provider",
    options=["mock", "openai"],
    index=0,
)

model = st.sidebar.text_input(
    "Model",
    value="gpt-5.5",
)

st.sidebar.markdown("---")

st.sidebar.write(
    """
    **Pipeline**

    1. Candidate Profile Builder
    2. Independent AI Personas
    3. Evidence-Based Debate
    4. Final Decision Engine
    5. Final Report
    """
)


# ---------------------------------------------------------
# File upload section
# ---------------------------------------------------------

st.header("1. Upload Evaluation Materials")

job_file = st.file_uploader(
    "Job Description",
    type=["pdf", "txt"],
    key="job_description",
)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Candidate A")

    resume_a = st.file_uploader(
        "Candidate A Resume",
        type=["pdf", "txt"],
        key="resume_a",
    )

    transcript_a = st.file_uploader(
        "Candidate A Interview Transcript",
        type=["pdf", "txt"],
        key="transcript_a",
    )

with col2:
    st.subheader("Candidate B")

    resume_b = st.file_uploader(
        "Candidate B Resume",
        type=["pdf", "txt"],
        key="resume_b",
    )

    transcript_b = st.file_uploader(
        "Candidate B Interview Transcript",
        type=["pdf", "txt"],
        key="transcript_b",
    )


# ---------------------------------------------------------
# Run evaluation
# ---------------------------------------------------------

st.markdown("---")

ready = all(
    [
        job_file,
        resume_a,
        transcript_a,
        resume_b,
        transcript_b,
    ]
)

if not ready:
    st.info(
        "Upload the Job Description plus resume and "
        "transcript for both candidates."
    )

run_button = st.button(
    "🚀 Run Multi-Agent Evaluation",
    type="primary",
    disabled=not ready,
    use_container_width=True,
)


if run_button:

    with tempfile.TemporaryDirectory() as temp_dir:

        temp_path = Path(temp_dir)

        input_dir = temp_path / "input"
        output_dir = temp_path / "output"

        input_dir.mkdir(parents=True, exist_ok=True)

        # Save inputs using the naming convention
        # already supported by batch.discover_candidates().
        save_uploaded_file(
            job_file,
            input_dir / "job_description.pdf",
        )

        save_uploaded_file(
            resume_a,
            input_dir / "candidate_A" / "resume.pdf",
        )

        save_uploaded_file(
            transcript_a,
            input_dir / "candidate_A" / "transcript.pdf",
        )

        save_uploaded_file(
            resume_b,
            input_dir / "candidate_B" / "resume.pdf",
        )

        save_uploaded_file(
            transcript_b,
            input_dir / "candidate_B" / "transcript.pdf",
        )

        config = {
            "provider": provider,
            "model": model,
        }

        try:
            with st.spinner(
                "Running profile extraction, four independent agents, "
                "three-round debate, and final decision..."
            ):

                job_path, candidates = discover_candidates(
                    input_dir
                )

                results = run_batch(
                    job_path=job_path,
                    candidate_paths=candidates,
                    config=config,
                    out_dir=output_dir,
                )

            st.success(
                "Evaluation completed successfully."
            )

            # Summary
            st.header("2. Evaluation Summary")

            summary_cols = st.columns(len(results))

            for column, (label, bundle) in zip(
                summary_cols,
                results.items(),
            ):
                with column:
                    st.subheader(
                        f"Candidate {label}"
                    )

                    st.metric(
                        "Recommendation",
                        recommendation_label(
                            bundle.decision.recommendation
                        ),
                    )

                    st.metric(
                        "Confidence",
                        f"{bundle.decision.confidence_percent}%",
                    )

                    st.write(
                        bundle.profile.candidate_name
                    )

            st.markdown("---")

            # Detailed results
            st.header("3. Detailed Evaluation")

            for label, bundle in results.items():

                with st.expander(
                    f"Candidate {label} — "
                    f"{bundle.profile.candidate_name}",
                    expanded=True,
                ):
                    render_candidate(
                        bundle,
                        label,
                    )

        except Exception as exc:
            st.error(
                "The evaluation could not be completed."
            )

            st.exception(exc)

            st.info(
                "For OpenAI mode, verify that OPENAI_API_KEY "
                "is configured in Streamlit Secrets."
            )

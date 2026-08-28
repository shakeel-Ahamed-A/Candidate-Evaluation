from __future__ import annotations
from pathlib import Path
from .ingestion import load_document


def discover_candidates(input_dir: Path):
    job_candidates = [input_dir / "job_description.pdf", input_dir / "02_Job_Description.pdf", input_dir / "job_description.txt"]
    job = next((p for p in job_candidates if p.exists()), None)
    if job is None:
        raise FileNotFoundError("Job description not found")
    pairs = {}
    for label in ("A", "B"):
        folder_resume = input_dir / f"candidate_{label}" / "resume.pdf"
        folder_transcript = input_dir / f"candidate_{label}" / "transcript.pdf"
        root_resume = input_dir / ("03_Resume_A.pdf" if label == "A" else "04_Resume_B.pdf")
        root_transcript = input_dir / ("05_Transcript_A.pdf" if label == "A" else "06_Transcript_B.pdf")
        resume = folder_resume if folder_resume.exists() else root_resume
        transcript = folder_transcript if folder_transcript.exists() else root_transcript
        if resume.exists() and transcript.exists():
            pairs[label] = (resume, transcript)
    if len(pairs) < 2:
        raise FileNotFoundError("Both Candidate A and Candidate B resume/transcript pairs are required")
    return job, pairs

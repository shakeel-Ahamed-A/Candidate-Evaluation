# Submission Checklist

This checklist maps the repository to the instructor's supplied problem statement.

| Instructor requirement | Implementation | Status |
|---|---|---|
| Candidate Profile Builder | `candidate_eval/profile_builder.py` | Complete |
| Shared factual profile | `CandidateProfile` with role profile, skills, experience, education, claims, certifications, metrics | Complete |
| Immutable after creation | Frozen nested models, tuple-backed collections, SHA-256 sidecar | Complete |
| Four distinct personas | `agents.py` + `prompts.py` | Complete |
| Independent LLM call per agent | One backend call per persona in independent stage | Complete |
| No cross-agent access before debate | Independent stage passes only the candidate profile + persona prompt | Complete |
| Evidence-backed findings | `EvidenceRef` + verbatim-quote validation | Complete |
| Real debate | Three rounds with direct responses | Complete |
| Opinion change recorded | `position_before`, `position_after`, `change_reason` | Complete |
| Final decision not simple averaging | Rule/gate engine in `decision.py` | Complete |
| Insufficient information handled | `MORE_INFO` outcome and escalation reasons | Complete |
| Final report | Markdown report with recommendation, confidence, strengths, concerns, disagreements, role fit | Complete |
| Process both candidates | Batch runner requires Candidate A and B | Complete |
| PDF source files | PyMuPDF ingestion for PDF inputs | Complete |
| Voice debate bonus | Not included in the required core pipeline; the assignment identifies it as a bonus | Optional |

## Expected input filenames

The runner supports the instructor's names directly:

```text
02_Job_Description.pdf
03_Resume_A.pdf
04_Resume_B.pdf
05_Transcript_A.pdf
06_Transcript_B.pdf
```

It also supports the cleaner folder layout documented in `README.md`.

## Not required by the supplied problem statement

The two-page statement does not require a presentation, a separate dataset, signed forms, a React frontend, a deployed URL, a specific page/word count, or a JavaScript package-lock file.

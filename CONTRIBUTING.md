# Contributing

Thanks for contributing to the AI Candidate Evaluation System.

## Development

1. Create a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Run the test suite with `pytest -q`.
4. Run the deterministic demo with `python main.py --mock`.

## Pull requests

Please keep changes focused, include tests for behavior changes, and update the README or configuration documentation when public behavior changes.

## Evaluation integrity

Changes must preserve the project's core guarantees: immutable candidate profiles, independent agent isolation before debate, evidence-backed findings, explicit debate rounds, and non-averaging decision logic.

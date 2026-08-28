from __future__ import annotations
import argparse, os
from pathlib import Path
import yaml
from dotenv import load_dotenv
from .batch import discover_candidates
from .orchestrator import run_batch


def build_parser():
    parser = argparse.ArgumentParser(description="Multi-Agent AI Interview Panel Simulator")
    parser.add_argument("--input-dir", type=Path, default=Path("sample"))
    parser.add_argument("--config", type=Path, default=Path("config/default.yaml"))
    parser.add_argument("--provider", choices=["mock", "openai"], default=None)
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    return parser


def main():
    load_dotenv()
    args = build_parser().parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    config["provider"] = args.provider or os.getenv("PROVIDER") or config.get("provider", "mock")
    job, candidates = discover_candidates(args.input_dir)
    results = run_batch(job, candidates, config, args.output_dir)
    print("Processed both candidates:")
    for label, bundle in results.items():
        print(f"  Candidate {label}: {bundle.profile.candidate_name} -> {bundle.decision.recommendation.upper()} ({bundle.decision.confidence_percent}%)")
    print(f"Manifest: {args.output_dir / 'batch_manifest.json'}")

if __name__ == "__main__":
    main()

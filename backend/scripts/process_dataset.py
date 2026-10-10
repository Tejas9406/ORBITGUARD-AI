"""CLI entry point for stage-one telemetry processing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.pipeline import process_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit and process local Telemanom telemetry.")
    parser.add_argument("--output", default="artifacts/processed")
    parser.add_argument("--window", type=int, default=100)
    parser.add_argument("--threshold", type=float, default=3.5)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    manifest = process_dataset(root, root / args.output, args.window, args.threshold)
    print(json.dumps({"audit": manifest["audit"], "processed_channels": len(manifest["channels"])}, indent=2))


if __name__ == "__main__":
    main()

"""Entry point for Workout Timer CLI/GUI."""

from __future__ import annotations

import argparse
from pathlib import Path

from timer.base import CountdownTimer
from gui.app import run_app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Workout Timer with GUI and CLI modes")
    parser.add_argument(
        "seconds",
        nargs="?",
        type=int,
        default=30,
        help="Duration for the CLI countdown (default: 30)",
    )
    parser.add_argument(
        "--label",
        type=str,
        default=None,
        help="Optional label for the CLI countdown",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run the timer in console mode instead of launching the GUI",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_dir = Path(__file__).resolve().parent
    if args.cli:
        timer = CountdownTimer(seconds=args.seconds, label=args.label)
        timer.start()
    else:
        run_app(base_dir)


if __name__ == "__main__":
    main()

"""Entry point per l'app Workout Timer."""

from __future__ import annotations

import argparse

from timer.base import WorkoutTimer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Timer a countdown per workout")
    parser.add_argument(
        "seconds",
        nargs="?",
        type=int,
        default=30,
        help="Durata in secondi del countdown (default: 30)",
    )
    parser.add_argument(
        "--label",
        type=str,
        default=None,
        help="Etichetta opzionale per identificare il timer",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    timer = WorkoutTimer(seconds=args.seconds, label=args.label)
    timer.start()


if __name__ == "__main__":
    main()

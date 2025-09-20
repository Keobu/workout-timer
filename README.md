# Workout Timer

Python application that delivers configurable workout timers via GUI and CLI. The GUI offers Tabata and Boxing presets with live phase updates, while the CLI keeps the original console countdown.

## Requirements

Install dependencies from `requirements.txt` (Python 3.10+ recommended):

```bash
pip install -r requirements.txt
```

## GUI Usage

Run the GUI (default) to configure a session visually:

```bash
python3 main.py
```

- **Tabata** tab: set preparation, work, rest, rounds, cycles, and cooldown. The display shows the current phase (e.g., `Work Round 2 Cycle 1`).
- **Boxing** tab: configure round length, rest interval, and number of rounds following the classic 3-min/1-min structure.
- Use **Start** to launch the sequence and **Stop** to reset the timer back to `00:00`.

## CLI Usage

Retain the console countdown with the `--cli` flag:

```bash
python3 main.py --cli 45 --label Warmup
```

This prints the remaining time in the terminal, useful for scripted or quick runs.

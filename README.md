# Workout Timer

![Workout Timer GUI](docs/workout-timer-gui.png)

Python application that delivers configurable workout timers via GUI and CLI. The GUI offers Tabata, Boxing, and Custom presets with live phase updates, while the CLI keeps the original console countdown.

## Requirements

Install dependencies from `requirements.txt` (Python 3.10+ recommended):

```bash
pip install -r requirements.txt
```

## GUI Modes

Run the GUI (default) to configure a session visually:

```bash
python3 main.py
```

### Tabata
- Configure preparation, work, rest, rounds, cycles, and cooldown.
- The display highlights the current round/cycle and phase (Work/Rest/Cooldown).

### Boxing
- Set classic boxing rounds (default 3 min work / 1 min rest).
- The label always shows the active round and whether you are in Work or Rest.

### Custom
- Provide your own list of intervals in the multiline field, one per line, e.g.:
  ```
  45, 15
  30, 10
  60, 0
  ```
- Each line represents a Work/Rest pair (rest is optional and defaults to 0). The timer executes the sequence in order.

Use **Start** to launch the selected program and **Stop** to reset the timer back to `00:00`.

## CLI Usage

Retain the console countdown with the `--cli` flag:

```bash
python3 main.py --cli 45 --label Warmup
```

This prints the remaining time in the terminal, useful for scripted or quick runs.

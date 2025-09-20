# Workout Timer

![Workout Timer GUI](docs/workout-timer-gui.png)

Python application that delivers configurable workout timers via GUI and CLI. The interface now features live duration summaries, customizable notification sounds, and a responsive layout that stays readable as you tweak parameters. The CLI keeps the original console countdown for lightweight usage.

## Highlights

- Live work/rest totals that update instantly when you edit inputs in any mode.
- Sound notifications with volume control, preview, and automatic macOS fallback playback.
- Responsive CustomTkinter UI with dedicated tabs for modes and settings to keep the workflow tidy.

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
- Configure preparation, work, rest, rounds, cycles, and cooldown. Each duration accepts seconds, values with suffix (`90s`, `2m`), or `mm:ss` (e.g., `1:30`).
- The display highlights the current round/cycle and phase (Work/Rest/Cooldown) while the summary panel tracks total work and rest time.

### Boxing
- Set classic boxing rounds (default 3 min work / 1 min rest). Work/rest inputs accept seconds or `mm:ss`.
- The label always shows the active round and whether you are in Work or Rest, and totals keep you aware of scheduled workload.

### Custom
- Provide your own list of intervals in the multiline field, one per line, e.g.:
  ```
  1:00, 0:30
  45, 15
  2m, 30s
  ```
- Each line represents a Work/Rest pair (rest is optional and defaults to 0). The timer executes the sequence in order and refreshes totals on every edit.

Use **Start** to launch the selected program and **Stop** to reset the timer back to `00:00`.

## Settings

- Pick the notification sound (WAV) with the file picker or reset to the bundled `assets/beep.wav`.
- Adjust volume via slider or numeric entry (0–100%).
- Use **Test Sound** to preview without saving; the app falls back to a system beep if playback fails.
- Hit **Save Settings** to persist your choices in `settings.json` and immediately apply them to the running timer.

## CLI Usage

Retain the console countdown with the `--cli` flag:

```bash
python3 main.py --cli 45 --label Warmup
```

This prints the remaining time in the terminal, useful for scripted or quick runs.

## Configuration Files

- `settings.json` records the sound path and volume for notifications.
- `assets/beep.wav` provides the default beep bundled with the application.

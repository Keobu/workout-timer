# Workout Timer

![Workout Timer GUI](docs/workout%20timer.png)

Python application that delivers configurable workout timers via GUI and CLI. The GUI offers Tabata, Boxing, and Custom presets with live phase updates, plus a Settings page for sound customization. The CLI keeps the original console countdown.

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
- Configure preparation, work, rest, rounds, cycles, and cooldown. Each duration accepts seconds or mm:ss (e.g., 1:30).
- The display highlights the current round/cycle and phase (Work/Rest/Cooldown).

### Boxing
- Set classic boxing rounds (default 3 min work / 1 min rest). Work/rest inputs accept seconds or mm:ss.
- The label always shows the active round and whether you are in Work or Rest.

### Custom
- Provide your own list of intervals in the multiline field, one per line, e.g.:
  ```
  45, 15
  30, 10
  60, 0
  ```
- Each line represents a Work/Rest pair (rest is optional and defaults to 0). You can write values as seconds or mm:ss (e.g., 0:45). The timer executes the sequence in order.

### Settings
- Pick the notification sound (WAV) using the file picker or reset to the bundled `assets/beep.wav`.
- Adjust volume with the slider or numeric entry (0–100%).
- Use **Save Settings** to persist your choices to `settings.json` and **Test Sound** to preview the selected file. Settings load automatically at startup.

Use **Start** to launch the selected program and **Stop** to reset the timer back to `00:00`.

## CLI Usage

Retain the console countdown with the `--cli` flag:

```bash
python3 main.py --cli 45 --label Warmup
```

This prints the remaining time in the terminal, useful for scripted or quick runs.

## Configuration Files

- `settings.json` records the sound path and volume for notifications.
- `assets/beep.wav` provides the default beep bundled with the application.

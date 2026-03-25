# ⏰ Python Alarm Clock

A clean, modular alarm clock with both a **CLI** and a **Tkinter GUI**, built with Python 3.8+.

---

## Features

| Feature | CLI | GUI |
|---|---|---|
| Set multiple alarms | ✅ | ✅ |
| View active alarms | ✅ | ✅ |
| Delete alarms | ✅ | ✅ |
| Snooze (5 minutes) | ✅ | ✅ |
| Input validation | ✅ | ✅ |
| Real-time clock display | ✅ (menu header) | ✅ (large digital) |
| Cross-platform sound | ✅ | ✅ |
| Background alarm checker | ✅ | ✅ |

---

## Project Structure

```
alarm_clock/
├── alarm_clock.py   ← CLI version (main logic + entry point)
├── alarm_gui.py     ← GUI version (Tkinter, imports alarm_clock.py)
└── README.md
```

---

## Requirements

### Python Version
Python **3.8 or higher** is required.
Check yours:
```bash
python --version
# or
python3 --version
```

### Libraries

| Library | Used for | Install needed? |
|---|---|---|
| `datetime` | Time handling | ❌ built-in |
| `threading` | Background alarm checker | ❌ built-in |
| `time` | sleep() loop | ❌ built-in |
| `platform` | Detect OS for sound | ❌ built-in |
| `winsound` | Beep sound on Windows | ❌ built-in (Windows only) |
| `tkinter` | GUI (alarm_gui.py) | ❌ built-in on Win/macOS |

> **Linux users only:** If Tkinter is missing, install it:
> ```bash
> # Ubuntu / Debian
> sudo apt install python3-tk
>
> # Fedora / RHEL
> sudo dnf install python3-tkinter
>
> # Arch
> sudo pacman -S tk
> ```

**No `pip install` is needed.** This project uses 100% standard library.

---

## How to Run

### Option 1 — CLI (Recommended for beginners)

```bash
cd alarm_clock
python alarm_clock.py
```

**Menu:**
```
┌─── Alarm Clock ─── 14:32:05 ──────────────┐
│  1.  Set Alarm                             │
│  2.  View Alarms                           │
│  3.  Delete Alarm                          │
│  4.  Exit                                  │
└────────────────────────────────────────────┘
```

### Option 2 — GUI (Tkinter)

```bash
cd alarm_clock
python alarm_gui.py
```

> **Note:** Both files must be in the **same folder** — `alarm_gui.py` imports from `alarm_clock.py`.

---

## How to Use

### Setting an Alarm

1. Choose **Set Alarm** (option 1 in CLI, `+ Set Alarm` button in GUI)
2. Enter time in **24-hour HH:MM format**
   - `07:30` → 7:30 AM
   - `22:15` → 10:15 PM
3. Enter an optional label (e.g. "Morning standup")

### When the Alarm Rings

The alarm will:
- Play a system sound
- Display: **"WAKE UP! ALARM RINGING!"**
- Ask you to **[S] Snooze** or **[D] Dismiss**

**Snooze** adds 5 minutes from the current time and rings again.

### Deleting an Alarm

1. Choose **Delete Alarm** (option 3 in CLI)
2. You'll see the list of active alarms with their IDs
3. Enter the ID number of the alarm you want to remove

---

## Cross-Platform Sound

| OS | Method | Requires install? |
|---|---|---|
| Windows | `winsound.Beep()` | No |
| macOS | `afplay` (system sound) | No |
| Linux | `paplay` / `aplay` → fallback terminal bell | No (uses pre-installed tools) |

---

## Common Issues

**Q: I don't hear any sound on Linux.**
A: The app falls back to a terminal bell (`\a`). Make sure your terminal is not muted, or install `pulseaudio-utils` for `paplay`.

**Q: `ModuleNotFoundError: No module named 'tkinter'` on Linux**
A: Run `sudo apt install python3-tk` then retry.

**Q: Alarm fires but I'm in the middle of typing in the CLI.**
A: Finish typing (or press Enter on an empty input). The alarm popup appears on your next menu loop iteration. The sound still plays immediately in the background.

---

## Design Notes (For Learning)

- **`AlarmManager`** runs a daemon thread that checks alarms every 1 second using `time.sleep(1)` — low CPU usage.
- **Thread-safety**: `threading.Lock` prevents race conditions between the UI thread and the checker thread.
- **`threading.Event`** is used as a signal flag — the checker sets it, the UI polls and clears it.
- **Modular**: `alarm_clock.py` is fully self-contained. `alarm_gui.py` simply imports and extends it.

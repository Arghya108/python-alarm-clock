#!/usr/bin/env python3
"""
=============================================================
  Alarm Clock - CLI Version
  Author  : Senior Python Developer
  Version : 1.0.0
  Python  : 3.8+
=============================================================
  Features:
    - Set multiple alarms (HH:MM, 24-hour)
    - View and delete alarms
    - Snooze (5 minutes) when alarm fires
    - Input validation
    - Background thread checks alarms without blocking UI
    - Cross-platform sound (Windows / macOS / Linux)
=============================================================
"""

import os
import sys
import platform
import threading
import time
from datetime import datetime, timedelta
from typing import List, Optional


# ─────────────────────────────────────────────
#  SOUND UTILITIES
# ─────────────────────────────────────────────

def play_sound() -> None:
    """
    Play an alert sound using the best available method
    for the current operating system.

    - Windows : winsound.Beep  (built-in, no install needed)
    - macOS   : afplay with system sound (built-in)
    - Linux   : paplay / aplay with system sound, fallback to bell
    """
    system = platform.system()

    try:
        if system == "Windows":
            import winsound
            for _ in range(3):
                winsound.Beep(1000, 500)   # 1000 Hz for 500 ms
                time.sleep(0.2)

        elif system == "Darwin":  # macOS
            # afplay is built into macOS — no install needed
            os.system("afplay /System/Library/Sounds/Glass.aiff 2>/dev/null || "
                       "afplay /System/Library/Sounds/Ping.aiff 2>/dev/null")

        else:  # Linux and others
            # Try common Linux sound players in order
            played = False
            sound_files = [
                "/usr/share/sounds/alsa/Front_Left.wav",
                "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga",
            ]
            players = ["paplay", "aplay", "ffplay -nodisp -autoexit -loglevel quiet"]

            for sound_file in sound_files:
                if os.path.exists(sound_file):
                    for player in players:
                        if os.system(f"which {player.split()[0]} > /dev/null 2>&1") == 0:
                            os.system(f"{player} '{sound_file}' 2>/dev/null")
                            played = True
                            break
                if played:
                    break

            # Final fallback: terminal bell character
            if not played:
                for _ in range(5):
                    print("\a", end="", flush=True)
                    time.sleep(0.4)

    except Exception:
        # Absolute last resort — terminal bell
        print("\a\a\a", end="", flush=True)


# ─────────────────────────────────────────────
#  ALARM CLASS
# ─────────────────────────────────────────────

class Alarm:
    """
    Represents a single alarm entry.

    Attributes
    ----------
    alarm_id   : Unique integer ID auto-assigned at creation.
    hour       : Target hour  (0–23).
    minute     : Target minute (0–59).
    label      : Human-readable label shown in alarm list.
    is_active  : False once alarm has fired (and not snoozed).
    snooze_until: datetime of snoozed ring time, or None.
    """

    _id_counter: int = 0  # class-level counter for unique IDs

    def __init__(self, hour: int, minute: int, label: str = "") -> None:
        Alarm._id_counter += 1
        self.alarm_id: int = Alarm._id_counter
        self.hour: int = hour
        self.minute: int = minute
        self.label: str = label.strip() or f"Alarm {self.alarm_id}"
        self.is_active: bool = True
        self.snooze_until: Optional[datetime] = None

    # ── Helpers ──────────────────────────────

    @property
    def time_str(self) -> str:
        """Return alarm time as HH:MM string."""
        return f"{self.hour:02d}:{self.minute:02d}"

    @property
    def is_snoozed(self) -> bool:
        """True if alarm is currently snoozed."""
        return self.snooze_until is not None

    def snooze(self, minutes: int = 5) -> None:
        """Snooze the alarm for `minutes` minutes from now."""
        self.snooze_until = datetime.now() + timedelta(minutes=minutes)
        self.is_active = True  # keep it alive

    def deactivate(self) -> None:
        """Mark alarm as fired — will be ignored by the checker."""
        self.is_active = False
        self.snooze_until = None

    def should_ring_now(self) -> bool:
        """
        Return True if the alarm should fire right now.

        Two cases:
        1. Normal alarm   — current HH:MM matches alarm HH:MM.
        2. Snoozed alarm  — current datetime >= snooze_until datetime.
        """
        now = datetime.now()

        if self.is_snoozed:
            # Snoozed alarms fire based on absolute datetime
            return now >= self.snooze_until

        # Normal: match on hour and minute only
        return now.hour == self.hour and now.minute == self.minute

    def __str__(self) -> str:
        if not self.is_active:
            status = "✓ Done"
        elif self.is_snoozed:
            t = self.snooze_until.strftime("%H:%M:%S")
            status = f"💤 Snoozed → rings at {t}"
        else:
            status = "🔔 Active"
        return f"  [{self.alarm_id}]  {self.time_str}  |  {self.label:<20}  |  {status}"


# ─────────────────────────────────────────────
#  ALARM MANAGER
# ─────────────────────────────────────────────

class AlarmManager:
    """
    Manages a list of alarms and runs a background daemon thread
    that checks every second whether any alarm should fire.

    Thread-safety is handled with threading.Lock so the UI thread
    and the checker thread never corrupt the alarms list.
    """

    SNOOZE_MINUTES: int = 5

    def __init__(self) -> None:
        self.alarms: List[Alarm] = []
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Flag set by checker thread to signal UI that an alarm fired
        self._pending_alarm: Optional[Alarm] = None
        self._alarm_event = threading.Event()

    # ── Lifecycle ────────────────────────────

    def start(self) -> None:
        """Start the background alarm-checker thread."""
        self._running = True
        self._thread = threading.Thread(
            target=self._checker_loop,
            daemon=True,   # thread dies when main program exits
            name="AlarmChecker"
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the background thread gracefully."""
        self._running = False

    # ── CRUD operations ──────────────────────

    def add_alarm(self, hour: int, minute: int, label: str = "") -> Alarm:
        """Create and register a new alarm. Returns the new Alarm."""
        alarm = Alarm(hour, minute, label)
        with self._lock:
            self.alarms.append(alarm)
        return alarm

    def get_active_alarms(self) -> List[Alarm]:
        """Return only alarms that are still active (not fired)."""
        with self._lock:
            return [a for a in self.alarms if a.is_active]

    def get_all_alarms(self) -> List[Alarm]:
        """Return all alarms including fired ones."""
        with self._lock:
            return list(self.alarms)

    def delete_alarm(self, alarm_id: int) -> bool:
        """
        Remove alarm by ID.
        Returns True on success, False if ID not found.
        """
        with self._lock:
            for i, alarm in enumerate(self.alarms):
                if alarm.alarm_id == alarm_id:
                    self.alarms.pop(i)
                    return True
        return False

    def snooze_alarm(self, alarm: Alarm) -> None:
        """Snooze a fired alarm for SNOOZE_MINUTES minutes."""
        with self._lock:
            alarm.snooze(self.SNOOZE_MINUTES)

    def dismiss_alarm(self, alarm: Alarm) -> None:
        """Permanently dismiss a fired alarm."""
        with self._lock:
            alarm.deactivate()

    # ── Background checker ───────────────────

    def _checker_loop(self) -> None:
        """
        Runs in a background daemon thread.
        Checks every second if any alarm should ring.
        Uses sleep(1) — minimal CPU usage.
        """
        # Track which alarms already fired this minute to prevent
        # re-firing every second within the same minute.
        fired_this_minute: set = set()

        while self._running:
            now = datetime.now()
            minute_key = (now.hour, now.minute)

            # Reset fired set when minute changes
            fired_this_minute = {
                key for key in fired_this_minute
                if key == minute_key
            }

            with self._lock:
                alarms_snapshot = list(self.alarms)

            for alarm in alarms_snapshot:
                if not alarm.is_active:
                    continue

                # For snoozed alarms use a different dedupe key
                dedupe_key = (alarm.alarm_id, alarm.snooze_until or minute_key)

                if alarm.should_ring_now() and dedupe_key not in fired_this_minute:
                    fired_this_minute.add(dedupe_key)

                    # Clear snooze so it doesn't immediately re-fire
                    with self._lock:
                        alarm.snooze_until = None

                    # Signal the UI thread
                    self._pending_alarm = alarm
                    self._alarm_event.set()

                    # Play sound in this checker thread (non-blocking for UI)
                    play_sound()

            time.sleep(1)


# ─────────────────────────────────────────────
#  INPUT HELPERS
# ─────────────────────────────────────────────

def parse_time(time_str: str):
    """
    Parse a time string in HH:MM format (24-hour).

    Returns (hour, minute) tuple on success.
    Raises ValueError with a descriptive message on failure.
    """
    time_str = time_str.strip()

    if ":" not in time_str:
        raise ValueError("Missing ':' — use format HH:MM  (e.g. 07:30)")

    parts = time_str.split(":")
    if len(parts) != 2:
        raise ValueError("Too many ':' separators — use HH:MM format only")

    h_str, m_str = parts
    if not h_str.isdigit() or not m_str.isdigit():
        raise ValueError("Hour and minute must be numbers")

    hour = int(h_str)
    minute = int(m_str)

    if not (0 <= hour <= 23):
        raise ValueError(f"Hour must be 0–23, got {hour}")
    if not (0 <= minute <= 59):
        raise ValueError(f"Minute must be 0–59, got {minute}")

    return hour, minute


def prompt(message: str) -> str:
    """Wrapper around input() that handles KeyboardInterrupt cleanly."""
    try:
        return input(message)
    except KeyboardInterrupt:
        print("\n[Ctrl+C detected — returning to menu]")
        return ""


# ─────────────────────────────────────────────
#  MENU ACTIONS
# ─────────────────────────────────────────────

def action_set_alarm(manager: AlarmManager) -> None:
    """Prompt the user to set a new alarm."""
    print("\n── Set New Alarm ──────────────────────────")

    while True:
        raw = prompt("  Enter alarm time (HH:MM, 24-hr): ").strip()
        if not raw:
            print("  [Cancelled]")
            return
        try:
            hour, minute = parse_time(raw)
            break
        except ValueError as e:
            print(f"  ✗ Invalid input: {e}. Try again.\n")

    label = prompt("  Enter a label (optional, press Enter to skip): ").strip()

    alarm = manager.add_alarm(hour, minute, label)
    print(f"\n  ✔ Alarm [{alarm.alarm_id}] set for {alarm.time_str}  →  \"{alarm.label}\"")


def action_view_alarms(manager: AlarmManager) -> None:
    """Print the current list of active alarms."""
    print("\n── Active Alarms ──────────────────────────")
    alarms = manager.get_active_alarms()

    if not alarms:
        print("  (no active alarms)")
        return

    print(f"  {'ID':<5} {'Time':<8} {'Label':<22} Status")
    print("  " + "─" * 55)
    for alarm in alarms:
        print(alarm)


def action_delete_alarm(manager: AlarmManager) -> None:
    """Show active alarms and let the user delete one by ID."""
    print("\n── Delete Alarm ───────────────────────────")
    alarms = manager.get_active_alarms()

    if not alarms:
        print("  (no active alarms to delete)")
        return

    for alarm in alarms:
        print(alarm)

    raw = prompt("\n  Enter alarm ID to delete (or press Enter to cancel): ").strip()
    if not raw:
        print("  [Cancelled]")
        return

    if not raw.isdigit():
        print("  ✗ Invalid ID — must be a number")
        return

    alarm_id = int(raw)
    if manager.delete_alarm(alarm_id):
        print(f"  ✔ Alarm [{alarm_id}] deleted.")
    else:
        print(f"  ✗ No alarm with ID {alarm_id} found.")


def handle_ringing_alarm(manager: AlarmManager, alarm: Alarm) -> None:
    """
    Called from the main loop when an alarm fires.
    Prompts the user to snooze or dismiss.
    """
    print("\n" + "=" * 50)
    print("  🔔  WAKE UP!  ALARM RINGING!")
    print(f"  Alarm: [{alarm.alarm_id}]  {alarm.time_str}  —  {alarm.label}")
    print("=" * 50)
    print("  [S] Snooze for 5 minutes")
    print("  [D] Dismiss alarm")

    choice = prompt("  Your choice: ").strip().upper()

    if choice == "S":
        manager.snooze_alarm(alarm)
        snooze_time = alarm.snooze_until.strftime("%H:%M")
        print(f"  💤 Snoozed. Will ring again at {snooze_time}.")
    else:
        manager.dismiss_alarm(alarm)
        print("  ✔ Alarm dismissed.")


def print_menu() -> None:
    """Print the main menu."""
    now = datetime.now().strftime("%H:%M:%S")
    print(f"\n┌─── Alarm Clock ─── {now} ──────────────┐")
    print("│  1.  Set Alarm                             │")
    print("│  2.  View Alarms                           │")
    print("│  3.  Delete Alarm                          │")
    print("│  4.  Exit                                  │")
    print("└────────────────────────────────────────────┘")


# ─────────────────────────────────────────────
#  MAIN ENTRY POINT
# ─────────────────────────────────────────────

def main() -> None:
    """
    Entry point for the Alarm Clock CLI application.

    Starts the AlarmManager background thread, then runs
    a menu loop. Alarm notifications are checked each time
    the loop iterates (after user input returns).
    """
    print("\n  ====================================")
    print("       Python Alarm Clock  v1.0")
    print("  ====================================")
    print(f"  System  : {platform.system()} {platform.release()}")
    print(f"  Time now: {datetime.now().strftime('%H:%M:%S')}")
    print("  Type Ctrl+C inside any prompt to go back to menu.\n")

    manager = AlarmManager()
    manager.start()

    menu_actions = {
        "1": action_set_alarm,
        "2": action_view_alarms,
        "3": action_delete_alarm,
    }

    while True:
        # ── Check if any alarm fired since last loop ──
        if manager._alarm_event.is_set():
            manager._alarm_event.clear()
            pending = manager._pending_alarm
            if pending is not None:
                handle_ringing_alarm(manager, pending)
                manager._pending_alarm = None
            continue   # redraw menu after handling alarm

        print_menu()
        choice = prompt("  Choose an option [1-4]: ").strip()

        if choice == "4" or choice.lower() == "exit":
            active = manager.get_active_alarms()
            if active:
                confirm = prompt(
                    f"  You have {len(active)} active alarm(s). Exit anyway? [y/N]: "
                ).strip().lower()
                if confirm != "y":
                    continue
            manager.stop()
            print("\n  Goodbye! ⏰\n")
            sys.exit(0)

        elif choice in menu_actions:
            menu_actions[choice](manager)

        else:
            print("  ✗ Invalid option. Enter 1, 2, 3, or 4.")

        # ── Brief pause then re-check for fired alarms ──
        # This is a non-blocking poll — not a busy-wait.
        # The checker thread does the real 1-second sleep.
        time.sleep(0.1)

        if manager._alarm_event.is_set():
            manager._alarm_event.clear()
            pending = manager._pending_alarm
            if pending is not None:
                handle_ringing_alarm(manager, pending)
                manager._pending_alarm = None


if __name__ == "__main__":
    main()

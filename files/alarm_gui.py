#!/usr/bin/env python3
"""
=============================================================
  Alarm Clock - GUI Version (Tkinter)
  Author  : Senior Python Developer
  Version : 1.0.0
  Python  : 3.8+
  Requires: tkinter (built-in with standard Python on Windows/macOS)
            On Ubuntu/Debian: sudo apt install python3-tk
=============================================================
  Features:
    - Real-time digital clock display
    - Set / delete multiple alarms
    - Snooze popup with countdown
    - Cross-platform sound
    - Color-coded alarm list (active / snoozed / done)
=============================================================
"""

import os
import sys
import platform
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, timedelta
from typing import List, Optional

# Re-use the AlarmManager from the CLI module
# (Add parent dir to path in case this file is run directly)
sys.path.insert(0, os.path.dirname(__file__))
from alarm_clock import AlarmManager, Alarm, play_sound, parse_time


# ─────────────────────────────────────────────
#  COLOUR PALETTE  (dark, modern theme)
# ─────────────────────────────────────────────

COLORS = {
    "bg":           "#1a1a2e",   # deep navy
    "panel":        "#16213e",   # slightly lighter navy
    "accent":       "#0f3460",   # mid-blue
    "highlight":    "#e94560",   # vivid red-pink (clock digits)
    "green":        "#57cc99",   # success / active
    "yellow":       "#f4d03f",   # snoozed
    "muted":        "#6c757d",   # done / inactive
    "text":         "#e0e0e0",   # body text
    "text_dark":    "#a0a0b0",   # secondary text
    "btn_bg":       "#0f3460",
    "btn_fg":       "#e0e0e0",
    "btn_hover":    "#e94560",
}


# ─────────────────────────────────────────────
#  MAIN APPLICATION CLASS
# ─────────────────────────────────────────────

class AlarmClockApp(tk.Tk):
    """
    Root Tkinter window for the Alarm Clock GUI.

    Layout
    ------
    ┌────────────────────────────────┐
    │        DIGITAL CLOCK           │
    ├────────────────────────────────┤
    │  [Set Alarm]  [Delete Alarm]   │
    ├────────────────────────────────┤
    │        ALARM LIST              │
    │  ...                           │
    └────────────────────────────────┘
    """

    def __init__(self) -> None:
        super().__init__()

        self.title("⏰  Alarm Clock")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])

        # Centre window on screen
        win_w, win_h = 520, 540
        self.geometry(f"{win_w}x{win_h}+{(self.winfo_screenwidth() - win_w)//2}"
                      f"+{(self.winfo_screenheight() - win_h)//2}")

        # Alarm backend
        self.manager = AlarmManager()
        self.manager.start()

        self._build_ui()
        self._tick_clock()          # start the real-time clock
        self._poll_alarms()         # start alarm notification polling

    # ─────────────────────────────────────────
    #  UI CONSTRUCTION
    # ─────────────────────────────────────────

    def _build_ui(self) -> None:
        """Build all widgets."""
        self._build_clock_section()
        self._build_separator()
        self._build_controls_section()
        self._build_separator()
        self._build_alarm_list_section()

    def _build_clock_section(self) -> None:
        """Large digital clock at the top."""
        frame = tk.Frame(self, bg=COLORS["bg"], pady=20)
        frame.pack(fill="x")

        self.clock_label = tk.Label(
            frame,
            text="00:00:00",
            font=("Courier New", 52, "bold"),
            fg=COLORS["highlight"],
            bg=COLORS["bg"],
        )
        self.clock_label.pack()

        self.date_label = tk.Label(
            frame,
            text="",
            font=("Helvetica", 12),
            fg=COLORS["text_dark"],
            bg=COLORS["bg"],
        )
        self.date_label.pack()

    def _build_separator(self) -> None:
        """Thin horizontal line separator."""
        sep = tk.Frame(self, bg=COLORS["accent"], height=1)
        sep.pack(fill="x", padx=20)

    def _build_controls_section(self) -> None:
        """Buttons: Set Alarm / Delete Alarm."""
        frame = tk.Frame(self, bg=COLORS["bg"], pady=14)
        frame.pack(fill="x", padx=30)

        set_btn = self._make_button(frame, "＋  Set Alarm", self._open_set_alarm_dialog)
        set_btn.pack(side="left", expand=True, fill="x", padx=(0, 8))

        del_btn = self._make_button(frame, "✕  Delete Selected", self._delete_selected_alarm)
        del_btn.pack(side="left", expand=True, fill="x", padx=(8, 0))

    def _build_alarm_list_section(self) -> None:
        """Scrollable listbox showing all alarms."""
        header = tk.Frame(self, bg=COLORS["panel"])
        header.pack(fill="x", padx=20)

        tk.Label(
            header,
            text=" Active Alarms",
            font=("Helvetica", 11, "bold"),
            fg=COLORS["text"],
            bg=COLORS["panel"],
            pady=8,
        ).pack(side="left")

        self.alarm_count_label = tk.Label(
            header,
            text="0 alarms",
            font=("Helvetica", 10),
            fg=COLORS["text_dark"],
            bg=COLORS["panel"],
            pady=8,
        )
        self.alarm_count_label.pack(side="right", padx=10)

        list_frame = tk.Frame(self, bg=COLORS["panel"], padx=20, pady=10)
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        self.alarm_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            bg=COLORS["panel"],
            fg=COLORS["text"],
            selectbackground=COLORS["accent"],
            selectforeground=COLORS["text"],
            font=("Courier New", 11),
            borderwidth=0,
            highlightthickness=0,
            activestyle="none",
            height=10,
        )
        self.alarm_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.alarm_listbox.yview)

        # Placeholder text when no alarms
        self.alarm_listbox.insert(tk.END, "  (no alarms set yet)")

    # ─────────────────────────────────────────
    #  BUTTON FACTORY
    # ─────────────────────────────────────────

    def _make_button(self, parent, text: str, command) -> tk.Button:
        """Create a styled flat button with hover effect."""
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=("Helvetica", 11, "bold"),
            fg=COLORS["btn_fg"],
            bg=COLORS["btn_bg"],
            activeforeground=COLORS["btn_fg"],
            activebackground=COLORS["btn_hover"],
            relief="flat",
            padx=12,
            pady=8,
            cursor="hand2",
            borderwidth=0,
        )
        btn.bind("<Enter>", lambda e: btn.config(bg=COLORS["btn_hover"]))
        btn.bind("<Leave>", lambda e: btn.config(bg=COLORS["btn_bg"]))
        return btn

    # ─────────────────────────────────────────
    #  REAL-TIME CLOCK
    # ─────────────────────────────────────────

    def _tick_clock(self) -> None:
        """Update the clock label every 1 second."""
        now = datetime.now()
        self.clock_label.config(text=now.strftime("%H:%M:%S"))
        self.date_label.config(text=now.strftime("%A, %d %B %Y"))
        self.after(1000, self._tick_clock)

    # ─────────────────────────────────────────
    #  ALARM LIST REFRESH
    # ─────────────────────────────────────────

    def _refresh_alarm_list(self) -> None:
        """Rebuild the alarm listbox from the current alarm state."""
        self.alarm_listbox.delete(0, tk.END)
        alarms = self.manager.get_active_alarms()

        if not alarms:
            self.alarm_listbox.insert(tk.END, "  (no alarms set yet)")
            self.alarm_count_label.config(text="0 alarms")
            return

        self.alarm_count_label.config(text=f"{len(alarms)} alarm(s)")

        for alarm in alarms:
            if alarm.is_snoozed:
                t = alarm.snooze_until.strftime("%H:%M")
                entry = f"  [{alarm.alarm_id}]  {alarm.time_str}  💤 Snoozed → {t}  | {alarm.label}"
                color = COLORS["yellow"]
            else:
                entry = f"  [{alarm.alarm_id}]  {alarm.time_str}  🔔  {alarm.label}"
                color = COLORS["green"]

            self.alarm_listbox.insert(tk.END, entry)
            self.alarm_listbox.itemconfig(tk.END, fg=color)

    # ─────────────────────────────────────────
    #  ALARM POLLING — fires every 500 ms
    # ─────────────────────────────────────────

    def _poll_alarms(self) -> None:
        """
        Check if the AlarmManager has signalled a fired alarm.
        Runs on the Tkinter main thread via .after() — no thread issues.
        """
        if self.manager._alarm_event.is_set():
            self.manager._alarm_event.clear()
            alarm = self.manager._pending_alarm
            self.manager._pending_alarm = None
            if alarm:
                self._show_alarm_popup(alarm)

        self._refresh_alarm_list()
        self.after(500, self._poll_alarms)

    # ─────────────────────────────────────────
    #  DIALOGS
    # ─────────────────────────────────────────

    def _open_set_alarm_dialog(self) -> None:
        """Show a custom dialog to input alarm time and label."""
        dialog = tk.Toplevel(self)
        dialog.title("Set New Alarm")
        dialog.configure(bg=COLORS["bg"])
        dialog.resizable(False, False)

        # Centre over main window
        dialog.geometry(
            f"340x220+{self.winfo_x() + 90}+{self.winfo_y() + 160}"
        )
        dialog.grab_set()   # modal

        tk.Label(dialog, text="Alarm Time (HH:MM)",
                 font=("Helvetica", 11), fg=COLORS["text"],
                 bg=COLORS["bg"]).pack(pady=(20, 4))

        time_var = tk.StringVar()
        time_entry = tk.Entry(
            dialog, textvariable=time_var,
            font=("Courier New", 16, "bold"),
            justify="center",
            bg=COLORS["accent"], fg=COLORS["highlight"],
            insertbackground=COLORS["text"],
            relief="flat", width=10,
        )
        time_entry.pack(pady=4)
        time_entry.focus_set()

        tk.Label(dialog, text="Label (optional)",
                 font=("Helvetica", 11), fg=COLORS["text"],
                 bg=COLORS["bg"]).pack(pady=(12, 4))

        label_var = tk.StringVar()
        label_entry = tk.Entry(
            dialog, textvariable=label_var,
            font=("Helvetica", 11),
            bg=COLORS["accent"], fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat", width=24,
        )
        label_entry.pack(pady=4)

        error_label = tk.Label(dialog, text="", font=("Helvetica", 10),
                               fg=COLORS["highlight"], bg=COLORS["bg"])
        error_label.pack()

        def confirm(event=None):
            raw = time_var.get().strip()
            try:
                hour, minute = parse_time(raw)
            except ValueError as e:
                error_label.config(text=f"✗ {e}")
                return

            alarm = self.manager.add_alarm(hour, minute, label_var.get())
            self._refresh_alarm_list()
            dialog.destroy()

        time_entry.bind("<Return>", confirm)
        label_entry.bind("<Return>", confirm)

        btn_frame = tk.Frame(dialog, bg=COLORS["bg"])
        btn_frame.pack(pady=6)

        self._make_button(btn_frame, "✔  Set", confirm).pack(
            side="left", padx=6)
        self._make_button(btn_frame, "Cancel",
                          dialog.destroy).pack(side="left", padx=6)

    def _delete_selected_alarm(self) -> None:
        """Delete whichever alarm is selected in the listbox."""
        selection = self.alarm_listbox.curselection()
        if not selection:
            messagebox.showinfo("No Selection",
                                "Click an alarm in the list first.")
            return

        alarms = self.manager.get_active_alarms()
        if not alarms:
            return

        idx = selection[0]
        if idx >= len(alarms):
            return

        alarm = alarms[idx]
        confirmed = messagebox.askyesno(
            "Delete Alarm",
            f"Delete alarm [{alarm.alarm_id}] — {alarm.time_str} ({alarm.label})?"
        )
        if confirmed:
            self.manager.delete_alarm(alarm.alarm_id)
            self._refresh_alarm_list()

    def _show_alarm_popup(self, alarm: Alarm) -> None:
        """
        Modal popup that appears when an alarm fires.
        Offers Snooze (5 min) or Dismiss.
        """
        popup = tk.Toplevel(self)
        popup.title("⏰ ALARM!")
        popup.configure(bg=COLORS["bg"])
        popup.resizable(False, False)
        popup.geometry(
            f"360x240+{self.winfo_x() + 80}+{self.winfo_y() + 150}"
        )
        popup.grab_set()
        popup.attributes("-topmost", True)

        tk.Label(popup, text="🔔  WAKE UP!", font=("Helvetica", 22, "bold"),
                 fg=COLORS["highlight"], bg=COLORS["bg"]).pack(pady=(28, 6))

        tk.Label(popup,
                 text=f"{alarm.time_str}  —  {alarm.label}",
                 font=("Courier New", 14),
                 fg=COLORS["text"], bg=COLORS["bg"]).pack(pady=4)

        tk.Label(popup, text="Alarm ringing!", font=("Helvetica", 11),
                 fg=COLORS["text_dark"], bg=COLORS["bg"]).pack(pady=4)

        btn_frame = tk.Frame(popup, bg=COLORS["bg"])
        btn_frame.pack(pady=20)

        def snooze():
            self.manager.snooze_alarm(alarm)
            popup.destroy()
            self._refresh_alarm_list()

        def dismiss():
            self.manager.dismiss_alarm(alarm)
            popup.destroy()
            self._refresh_alarm_list()

        snooze_btn = self._make_button(btn_frame, "💤 Snooze 5 min", snooze)
        snooze_btn.pack(side="left", padx=10)

        dismiss_btn = self._make_button(btn_frame, "✔ Dismiss", dismiss)
        dismiss_btn.pack(side="left", padx=10)

    # ─────────────────────────────────────────
    #  CLEAN EXIT
    # ─────────────────────────────────────────

    def on_close(self) -> None:
        """Stop background thread before destroying the window."""
        self.manager.stop()
        self.destroy()


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

def main() -> None:
    """Launch the Tkinter Alarm Clock GUI."""
    app = AlarmClockApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()


if __name__ == "__main__":
    main()

import csv
from datetime import datetime
from pathlib import Path
import threading
import uuid
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QDateTime, QUrl, QRectF
from PySide6.QtGui import QDesktopServices, QPainter, QColor, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QTabWidget, QFrame, QProgressBar, QDialog,
    QFormLayout, QComboBox, QCheckBox, QLineEdit, QSpinBox, QDateTimeEdit,
    QDialogButtonBox, QFileDialog, QMessageBox, QTextBrowser, QSystemTrayIcon, QMenu)
from . import __version__, CODENAME
from .art import THEMES, FLOWERS, PATTERNS, GardenHeader, app_icon
from .content import TERMS, DASHBOARD, DOCS_PRICING, DOCS_PROTOCOL, demo_snapshot
from .model import windows, buckets, now_utc, timestamp, number, duration, manual_remaining
from .provider import read_account, ProviderError


def label(text, role="", tip="", wrap=False):
    widget = QLabel(str(text)); widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(wrap)
    if role:
        widget.setObjectName(role)
    if tip:
        widget.setToolTip(TERMS.get(tip, tip))
    widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return widget


def button(text, action, tip="", primary=False):
    widget = QPushButton(text); widget.clicked.connect(action)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    widget.setToolTip(TERMS.get(tip, tip))
    if primary:
        widget.setObjectName("primary")
    return widget


def clear(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            clear(item.layout())


def card():
    frame = QFrame(); frame.setObjectName("card")
    layout = QVBoxLayout(frame); layout.setContentsMargins(16, 13, 16, 13); layout.setSpacing(6)
    return frame, layout


def metric(value, title, tip):
    frame, layout = card()
    layout.addWidget(label(value, "metric", tip)); layout.addWidget(label(title, "muted", tip))
    return frame


class Worker(QThread):
    success = Signal(dict)
    failure = Signal(str)
    auth_url = Signal(str)

    def __init__(self, path, sign_in, parent):
        super().__init__(parent); self.path = path; self.sign_in = sign_in; self.cancel = threading.Event()

    def run(self):
        try:
            self.success.emit(read_account(self.path, self.sign_in, self.auth_url.emit, self.cancel))
        except (ProviderError, OSError) as error:
            self.failure.emit(str(error))
        except Exception:
            self.failure.emit("This reading could not be interpreted. Your previous reading has been kept. Try updating Codex.")


class ActivityPlot(QWidget):
    def __init__(self, daily, theme):
        super().__init__(); self.theme = theme
        self.rows = []
        for row in daily or []:
            try:
                day = datetime.strptime(row.get("startDate", ""), "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue
            count = number(row.get("tokens"))
            if count is not None and count >= 0:
                self.rows.append((day, count))
        self.rows = sorted(dict(self.rows).items())[-14:]
        self.setFixedHeight(124)
        self.setAccessibleName("Recent reported daily token activity")
        self.setToolTip("Reported days only; missing days are not filled with zeros.\n" +
                        "\n".join(f"{day}: {int(count):,} tokens" for day, count in self.rows))

    def paintEvent(self, event):
        if not self.rows:
            return
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        width = self.width(); maximum = max(1, max(row[1] for row in self.rows))
        step = (width - 12) / len(self.rows)
        p.setPen(Qt.PenStyle.NoPen)
        for index, (_, count) in enumerate(self.rows):
            height = max(2, count / maximum * 76)
            p.setBrush(QColor(self.theme.accent if index == len(self.rows) - 1 else self.theme.petal))
            p.drawRoundedRect(QRectF(6 + index * step, 86 - height, max(3, step - 7), height), 4, 4)
        p.setPen(QColor(self.theme.muted)); p.setFont(QFont("Segoe UI", 8))
        p.drawText(6, 110, self.rows[0][0].strftime("%b %d"))
        p.drawText(width - 52, 110, self.rows[-1][0].strftime("%b %d"))
        p.end()


class Settings(QDialog):
    def __init__(self, state, parent):
        super().__init__(parent); self.setWindowTitle("Make it your garden"); self.resize(435, 400)
        layout = QVBoxLayout(self); form = QFormLayout(); self.controls = {}
        layout.addWidget(label("A garden of your own", "heading"))
        for key, title, choices in (("theme", "Palette", THEMES), ("flower", "Flower", FLOWERS), ("pattern", "Pattern", PATTERNS)):
            combo = QComboBox(); combo.addItems(list(choices)); combo.setCurrentText(state[key])
            form.addRow(title, combo); self.controls[key] = combo
        self.top = QCheckBox("Keep above other windows"); self.top.setChecked(bool(state["always_on_top"]))
        self.compact = QCheckBox("Compact overview"); self.compact.setChecked(bool(state["compact"]))
        form.addRow(self.top); form.addRow(self.compact)
        self.interval = QComboBox()
        for seconds, text in ((60, "Every minute"), (300, "Every 5 minutes"), (900, "Every 15 minutes"), (0, "Only when I click Refresh")):
            self.interval.addItem(text, seconds)
        self.interval.setCurrentIndex(max(0, self.interval.findData(state["refresh_seconds"])))
        self.interval.setToolTip(TERMS["Refresh"]); form.addRow("Readings", self.interval)
        self.path = QLineEdit(state["codex_path"]); self.path.setPlaceholderText("Automatic · bundled Codex first")
        form.addRow("Codex executable", self.path)
        layout.addLayout(form)
        layout.addWidget(button("Choose codex.exe…", self.browse))
        layout.addWidget(label("The Windows download includes Codex. Sign-in is handled by OpenAI in your browser. Your credentials stay with Codex.", "muted", wrap=True))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); layout.addWidget(buttons)

    def browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select the native Codex executable", "", "Executables (*.exe);;All files (*)")
        if path:
            self.path.setText(path)

    def values(self):
        return {**{key: control.currentText() for key, control in self.controls.items()},
                "always_on_top": self.top.isChecked(), "compact": self.compact.isChecked(),
                "refresh_seconds": self.interval.currentData(), "codex_path": self.path.text().strip()}


class ManualEditor(QDialog):
    def __init__(self, tracker, parent):
        super().__init__(parent); self.setWindowTitle("Record a usage limit"); self.resize(420, 360)
        self.tracker = tracker or {}; layout = QVBoxLayout(self); form = QFormLayout()
        layout.addWidget(label("Record what your account shows", "heading"))
        self.name = QLineEdit(self.tracker.get("name", "")); self.name.setMaxLength(80)
        self.name.setPlaceholderText("For example: ChatGPT research")
        self.cap = QSpinBox(); self.cap.setRange(1, 1000000); self.cap.setValue(int(self.tracker.get("cap", 100)))
        self.used = QSpinBox(); self.used.setRange(0, 10000000); self.used.setValue(int(self.tracker.get("used", 0)))
        self.units = QComboBox(); self.units.addItems(["messages", "tasks", "minutes", "percent", "uses"])
        self.units.setCurrentText(self.tracker.get("units", "messages"))
        self.has_reset = QCheckBox("The account shows a reset time")
        self.has_reset.setChecked(self.tracker.get("reset") is not None)
        self.reset = QDateTimeEdit(); self.reset.setCalendarPopup(True); self.reset.setDisplayFormat("MMM d, yyyy  h:mm AP")
        self.reset.setDateTime(QDateTime.fromSecsSinceEpoch(int(self.tracker.get("reset") or now_utc().timestamp() + 18000)))
        self.reset.setEnabled(self.has_reset.isChecked()); self.has_reset.toggled.connect(self.reset.setEnabled)
        for text, control in (("Name", self.name), ("Total allowance", self.cap), ("Used", self.used), ("Units", self.units)):
            form.addRow(text, control)
        form.addRow(self.has_reset); form.addRow("Reset · computer's time zone", self.reset)
        layout.addLayout(form); layout.addWidget(label(TERMS["Manual tracker"], "muted", wrap=True))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.validate); buttons.rejected.connect(self.reject); layout.addWidget(buttons)

    def validate(self):
        if not self.name.text().strip():
            self.name.setFocus(); self.name.setPlaceholderText("Please give this tracker a name")
            return
        self.accept()

    def value(self):
        return {"id": self.tracker.get("id", str(uuid.uuid4())), "name": self.name.text().strip(),
                "cap": self.cap.value(), "used": self.used.value(), "units": self.units.currentText(),
                "reset": self.reset.dateTime().toSecsSinceEpoch() if self.has_reset.isChecked() else None,
                "observed_at": now_utc().timestamp()}


class GardenWindow(QMainWindow):
    def __init__(self, store, demo=False, offline=False):
        super().__init__(); self.store = store; self.state = store.state
        for key, choices, fallback in (("theme", THEMES, "Rosewater"), ("flower", FLOWERS, "Cosmos"), ("pattern", PATTERNS, "Meadow")):
            if self.state.get(key) not in choices:
                self.state[key] = fallback
        self.demo = demo; self.sample = demo_snapshot(); self.offline = offline
        self.worker = None; self.live = False; self.error = store.warning; self.quitting = False
        self.reset_labels = []; self.gauges = []
        self.setWindowTitle(f"Usage Garden · {CODENAME} {__version__}"); self.setMinimumSize(390, 530)
        self.resize(440, 665) if self.state["compact"] else self.resize(478, 824)
        body = QWidget(); self.setCentralWidget(body); root = QVBoxLayout(body)
        root.setContentsMargins(0, 0, 0, 10); root.setSpacing(8)
        self.header = GardenHeader(); root.addWidget(self.header)
        toolbar = QHBoxLayout(); toolbar.setContentsMargins(16, 0, 16, 0)
        self.status = label("Not connected", "badge", "Cached reading"); toolbar.addWidget(self.status); toolbar.addStretch()
        self.pin = button("Pin", self.toggle_pin, "Keep this widget above other windows.")
        self.pin.setCheckable(True); toolbar.addWidget(self.pin)
        toolbar.addWidget(button("Garden…", self.settings, "Choose flowers, colors, patterns, and connection settings."))
        root.addLayout(toolbar)
        self.notice = label("", "notice", wrap=True); self.notice.setContentsMargins(16, 0, 16, 0); root.addWidget(self.notice)
        self.tabs = QTabWidget(); self.layouts = {}
        for title in ("Overview", "Activity", "Manual"):
            scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
            content = QWidget(); layout = QVBoxLayout(content); layout.setContentsMargins(16, 12, 16, 8)
            layout.setSpacing(10); self.layouts[title] = layout; scroll.setWidget(content); self.tabs.addTab(scroll, title)
        root.addWidget(self.tabs, 1)
        controls = QHBoxLayout(); controls.setContentsMargins(16, 0, 16, 0)
        self.refresh_button = button("Refresh", self.refresh, "Refresh", True)
        self.login_button = button("Sign in", lambda: self.refresh(True), "Connect through OpenAI's browser sign-in, using Codex.")
        self.cancel_button = button("Cancel", self.cancel_work, "Cancel the current connection attempt."); self.cancel_button.hide()
        controls.addWidget(self.refresh_button); controls.addWidget(self.login_button); controls.addWidget(self.cancel_button)
        controls.addWidget(button("Usage dashboard ↗", lambda: QDesktopServices.openUrl(QUrl(DASHBOARD)), "Open OpenAI's account usage dashboard."))
        root.addLayout(controls)
        footer = QHBoxLayout(); footer.setContentsMargins(16, 0, 16, 0)
        footer.addWidget(button("Field guide", self.guide, "Plain-language definitions and official sources."))
        self.preview_button = button("Preview garden", self.toggle_demo, "See clearly labeled sample readings without changing account data.")
        footer.addWidget(self.preview_button); footer.addStretch(); root.addLayout(footer)
        self.tray = QSystemTrayIcon(self); menu = QMenu()
        menu.addAction("Show Usage Garden", self.restore_window); menu.addAction("Refresh readings", self.refresh)
        menu.addSeparator(); menu.addAction("Quit", self.quit_app); self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.restore_window() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self.refresh)
        QShortcut(QKeySequence("F1"), self, activated=self.guide)
        QShortcut(QKeySequence("Ctrl+Q"), self, activated=self.quit_app)
        self.tick_timer = QTimer(self); self.tick_timer.timeout.connect(self.tick); self.tick_timer.start(1000)
        self.poll_timer = QTimer(self); self.poll_timer.timeout.connect(self.refresh)
        self.apply_theme(); self.update_polling(); self.render()
        if not demo and not offline:
            QTimer.singleShot(200, self.refresh)

    def save(self):
        try:
            self.store.save()
        except (OSError, ValueError):
            self.error = "Changes are visible but could not be saved. Check that your local data folder is writable."
            self.update_status()

    def snapshot(self):
        return self.sample if self.demo else self.state.get("snapshot")

    def apply_theme(self):
        t = THEMES[self.state["theme"]]; self.theme = t
        self.header.theme = t; self.header.species = self.state["flower"]; self.header.pattern = self.state["pattern"]
        self.header.setFixedHeight(110 if self.state["compact"] else 126); self.header.update()
        self.setStyleSheet(f"""
            QWidget {{ color: {t.ink}; font-family: 'Segoe UI'; font-size: 10pt; }}
            QMainWindow, QDialog, QScrollArea, QScrollArea > QWidget > QWidget {{ background: {t.background}; }}
            QFrame#card {{ background: {t.paper}; border: 1px solid {t.border}; border-radius: 14px; }}
            QLabel {{ background: transparent; }}
            QLabel#heading {{ font-family: Georgia; font-size: 17pt; }}
            QLabel#metric {{ font-size: 22pt; font-weight: 600; }}
            QLabel#muted {{ color: {t.muted}; font-size: 9pt; }}
            QLabel#badge {{ color: {t.accent}; font-weight: 600; font-size: 9pt; }}
            QLabel#notice {{ color: {t.accent}; font-size: 9pt; }}
            QPushButton {{ background: {t.paper}; border: 1px solid {t.border}; border-radius: 8px; padding: 7px 10px; }}
            QPushButton:hover, QPushButton:checked {{ background: {t.soft}; border-color: {t.accent}; }}
            QPushButton:focus {{ border: 2px solid {t.accent}; }}
            QPushButton:disabled {{ color: {t.muted}; background: {t.background}; }}
            QPushButton#primary {{ background: {t.accent}; color: {t.background}; border-color: {t.accent}; font-weight: 600; }}
            QTabWidget::pane {{ border: 0; }}
            QTabBar::tab {{ padding: 9px 18px; color: {t.muted}; border-bottom: 2px solid {t.border}; }}
            QTabBar::tab:selected {{ color: {t.accent}; border-bottom: 2px solid {t.accent}; }}
            QProgressBar {{ background: {t.soft}; border: 0; border-radius: 4px; min-height: 8px; max-height: 8px; }}
            QProgressBar::chunk {{ background: {t.accent}; border-radius: 4px; }}
            QToolTip {{ background: {t.paper}; color: {t.ink}; border: 1px solid {t.accent}; padding: 8px; }}
            QLineEdit, QSpinBox, QDateTimeEdit, QComboBox, QTextBrowser {{ background: {t.paper}; color: {t.ink}; border: 1px solid {t.border}; padding: 6px; border-radius: 5px; }}
            QComboBox QAbstractItemView, QMenu {{ background: {t.paper}; color: {t.ink}; selection-background-color: {t.soft}; }}
            QScrollBar:vertical {{ background: {t.background}; width: 10px; }}
            QScrollBar::handle:vertical {{ background: {t.border}; border-radius: 5px; min-height: 25px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        icon = app_icon(t, self.state["flower"]); self.setWindowIcon(icon); self.tray.setIcon(icon)
        was_visible = self.isVisible(); self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, bool(self.state["always_on_top"]))
        self.pin.setChecked(bool(self.state["always_on_top"]))
        if was_visible:
            self.show()

    def update_polling(self):
        seconds = self.state.get("refresh_seconds", 300)
        if not isinstance(seconds, int) or seconds not in (0, 60, 300, 900):
            seconds = 300
        self.poll_timer.stop()
        if seconds and not self.offline and not self.demo:
            self.poll_timer.start(seconds * 1000)

    def update_status(self):
        snapshot = self.snapshot(); observed = timestamp(snapshot.get("observed_at")) if snapshot else None
        if self.demo:
            text = "SAMPLE · invented readings"
        elif self.worker and self.worker.isRunning():
            text = "Connecting…" if self.worker.sign_in else "Refreshing…"
        elif observed:
            stale = (now_utc() - observed).total_seconds() > 600
            prefix = "Cached" if not self.live or stale or self.error else "Updated"
            text = f"{prefix} · {observed.astimezone():%b %d, %I:%M %p}"
        else:
            text = "Not connected"
        self.status.setText(text)
        self.notice.setText("Preview only. These numbers do not describe your account." if self.demo else self.error)
        self.notice.setVisible(bool(self.notice.text()))
        self.preview_button.setText("Back to my readings" if self.demo else "Preview garden")
        self.tray.setToolTip("Usage Garden · " + text)

    def render(self):
        self.reset_labels = []; self.gauges = []
        for layout in self.layouts.values():
            clear(layout)
        snapshot = self.snapshot(); overview = self.layouts["Overview"]
        if not snapshot:
            frame, layout = card(); layout.addWidget(label("Welcome to your garden", "heading"))
            layout.addWidget(label("Connect your ChatGPT account to gather your available usage windows, reset times, credits, and activity in one place.", wrap=True))
            layout.addWidget(label("Choose Sign in below. You can also preview the flowers or record a limit on the Manual tab.", "muted", wrap=True))
            overview.addWidget(frame)
        else:
            overview.addWidget(label(f"{snapshot.get('plan', 'Not reported').replace('_', ' ').title()}  ·  Connected plan", "muted", "Plan"))
            all_windows = windows(snapshot.get("limits", {}))
            if not all_windows:
                frame, layout = card(); layout.addWidget(label("Allowances not reported", "heading"))
                layout.addWidget(label("This account did not return usage windows. That does not mean zero usage or unlimited access.", "muted", "Not reported", True)); overview.addWidget(frame)
            for window in all_windows:
                frame, layout = card(); title = QHBoxLayout()
                title.addWidget(label(window.label, "", "Usage window")); title.addStretch()
                value = label("Not reported" if window.remaining is None else f"{window.remaining:g}% left", "metric", "Remaining")
                layout.addLayout(title); layout.addWidget(value)
                if window.remaining is not None:
                    gauge = QProgressBar(); gauge.setRange(0, 1000); gauge.setValue(round(min(100, window.remaining) * 10)); gauge.setTextVisible(False)
                    gauge.setAccessibleName(window.label + " remaining"); gauge.setToolTip(TERMS["Remaining"])
                    layout.addWidget(gauge); self.gauges.append((window, gauge, value))
                subtitle = window.name + (f" · {window.used:g}% used" if window.used is not None else "")
                if not self.state["compact"]:
                    layout.addWidget(label(subtitle, "muted", "Usage bucket", True))
                else:
                    value.setToolTip(TERMS["Remaining"] + "\n\n" + subtitle)
                reset = label(window.countdown(now_utc()), "badge", "Reset", True)
                if window.reset:
                    reset.setToolTip(TERMS["Reset"] + f"\n\nReported reset: {window.reset.astimezone():%A, %B %d, %Y at %I:%M:%S %p %Z}")
                layout.addWidget(reset); self.reset_labels.append((window, reset))
                if window.reached:
                    layout.addWidget(label(f"Service limit status: {window.reached}", "notice", wrap=True))
                overview.addWidget(frame)
            limits = snapshot.get("limits", {})
            credit_rows = [(key, row.get("credits")) for key, row in buckets(limits) if isinstance(row.get("credits"), dict)]
            for key, credits in credit_rows:
                value = "Unlimited" if credits.get("unlimited") is True else str(credits.get("balance", "Not reported"))
                if self.state["compact"]:
                    frame, box = card(); box.addWidget(label(f"Credits · {key}: {value}", "badge", "Credits")); overview.addWidget(frame)
                else:
                    overview.addWidget(metric(value, f"Credits · {key}", "Credits"))
            if not credit_rows and not self.state["compact"]:
                overview.addWidget(metric("Not reported", "Credit balance", "Credits"))
            resets = limits.get("rateLimitResetCredits") or {}; count = number(resets.get("availableCount"))
            frame, layout = card(); row = QHBoxLayout()
            row.addWidget(label("Earned resets", "", "Earned resets")); row.addStretch()
            row.addWidget(label("Not reported" if count is None else f"{count:g} available", "badge", "Earned resets")); layout.addLayout(row)
            expirations = [timestamp(item.get("expiresAt")) for item in resets.get("credits", []) if isinstance(item, dict)]
            expirations = [item for item in expirations if item]
            if expirations:
                layout.addWidget(label(f"Earliest reported expiry: {min(expirations).astimezone():%b %d, %I:%M %p}", "muted", "Earned resets"))
            overview.addWidget(frame)
        overview.addWidget(label("Work and Codex share usage. Other ChatGPT limits may need a manual tracker.", "muted", "Allowance", True)); overview.addStretch()
        self.render_activity(snapshot); self.render_manual(); self.update_status(); self.tick()

    def render_activity(self, snapshot):
        layout = self.layouts["Activity"]; activity = (snapshot or {}).get("activity", {}); summary = activity.get("summary", {})
        layout.addWidget(label("Your work, in numbers", "heading"))
        layout.addWidget(label("Service-reported token activity. These totals are not a bill or a remaining allowance.", "muted", "Tokens", True))
        if (snapshot or {}).get("activity_error"):
            layout.addWidget(label(snapshot["activity_error"], "notice", wrap=True))
        for key, title, term in (("lifetimeTokens", "Lifetime tokens", "Lifetime tokens"), ("peakDailyTokens", "Peak daily tokens", "Peak daily tokens"),
                                  ("longestRunningTurnSec", "Longest turn", "Longest turn"), ("currentStreakDays", "Current streak · days", "Streak"),
                                  ("longestStreakDays", "Longest streak · days", "Streak")):
            value = number(summary.get(key))
            text = "Not reported" if value is None else (duration(value) if key == "longestRunningTurnSec" and value > 0 else f"{value:,.0f}")
            layout.addWidget(metric(text, title, term))
        if activity.get("dailyUsageBuckets"):
            frame, box = card(); box.addWidget(label("Recent reported days", "", "Tokens"))
            box.addWidget(ActivityPlot(activity["dailyUsageBuckets"], self.theme)); layout.addWidget(frame)
        if not self.demo:
            layout.addWidget(button("Export recorded readings…", self.export_history, "Export this widget's last 500 successful allowance observations as CSV."))
        layout.addStretch()

    def render_manual(self):
        layout = self.layouts["Manual"]; layout.addWidget(label("A place for other limits", "heading"))
        layout.addWidget(label("Copy a number from your account's limit notice. These entries are manual and remain separate from live readings.", "muted", "Manual tracker", True))
        if self.demo:
            layout.addWidget(label("Leave the preview to view or edit your manual trackers.", "badge", wrap=True)); layout.addStretch(); return
        layout.addWidget(button("+ Record a limit", lambda: self.edit_manual(None), "Manual tracker", True))
        for tracker in self.state["manual"]:
            if not isinstance(tracker, dict):
                continue
            frame, box = card(); box.addWidget(label(tracker.get("name", "Manual limit"), "", "Manual tracker", True))
            remaining = manual_remaining(tracker)
            box.addWidget(label("Not recorded" if remaining is None else f"{remaining:g} {tracker.get('units', 'uses')} left", "metric", "Manual tracker", True))
            box.addWidget(label(f"MANUAL · {tracker.get('used', '?')} / {tracker.get('cap', '?')} used", "badge", "Manual tracker"))
            reset = timestamp(tracker.get("reset"))
            if reset:
                text = "Reset due · check your account" if reset <= now_utc() else f"Recorded reset: {reset.astimezone():%b %d, %I:%M %p}"
                box.addWidget(label(text, "muted", "Reset"))
            row = QHBoxLayout()
            row.addWidget(button("+1 used", lambda checked=False, t=tracker: self.increment(t), "Record one additional use yourself."))
            row.addWidget(button("Edit", lambda checked=False, t=tracker: self.edit_manual(t)))
            row.addWidget(button("Remove", lambda checked=False, t=tracker: self.remove_manual(t)))
            box.addLayout(row); layout.addWidget(frame)
        layout.addStretch()

    def tick(self):
        now = now_utc()
        for window, text in self.reset_labels:
            text.setText(window.countdown(now))
        for window, gauge, value in self.gauges:
            expired = window.expired(now); gauge.setEnabled(not expired)
            value.setText(f"{window.remaining:g}% at last reading" if expired else f"{window.remaining:g}% left")
        self.update_status()

    def refresh(self, sign_in=False):
        if self.demo:
            if sign_in:
                self.demo = False; self.update_polling(); self.render()
            else:
                return
        if self.offline or (self.worker and self.worker.isRunning()):
            return
        self.worker = Worker(self.state["codex_path"], bool(sign_in), self)
        self.worker.success.connect(self.received); self.worker.failure.connect(self.failed)
        self.worker.auth_url.connect(lambda url: QDesktopServices.openUrl(QUrl(url)))
        self.worker.finished.connect(self.worker_finished)
        self.refresh_button.setEnabled(False); self.login_button.setEnabled(False); self.cancel_button.show()
        self.worker.start(); self.update_status()

    def received(self, snapshot):
        self.live = True; self.error = ""; self.state["snapshot"] = snapshot
        self.state["history"].append({"observed_at": snapshot["observed_at"], "limits": snapshot["limits"]})
        self.save(); self.render()

    def failed(self, error):
        self.live = False; self.error = error; self.update_status()

    def worker_finished(self):
        self.refresh_button.setEnabled(True); self.login_button.setEnabled(True); self.cancel_button.hide()
        self.worker.deleteLater(); self.worker = None; self.update_status()

    def cancel_work(self):
        if self.worker:
            self.worker.cancel.set()

    def toggle_demo(self):
        if self.worker and self.worker.isRunning():
            return
        self.demo = not self.demo; self.update_polling(); self.render()

    def toggle_pin(self):
        self.state["always_on_top"] = not self.state["always_on_top"]; self.apply_theme(); self.save()

    def settings(self):
        dialog = Settings(self.state, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            old_compact = self.state["compact"]
            self.state.update(dialog.values()); self.apply_theme(); self.update_polling(); self.save(); self.render()
            if self.state["compact"] != old_compact:
                self.resize(440, 665) if self.state["compact"] else self.resize(478, 824)

    def edit_manual(self, tracker):
        dialog = ManualEditor(tracker, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            value = dialog.value()
            if tracker:
                tracker.update(value)
            else:
                self.state["manual"].append(value)
            self.save(); self.render()

    def increment(self, tracker):
        tracker["used"] = min(10000000, int(tracker.get("used", 0)) + 1)
        tracker["observed_at"] = now_utc().timestamp(); self.save(); self.render()

    def remove_manual(self, tracker):
        if QMessageBox.question(self, "Remove manual tracker", f"Remove ‘{tracker.get('name', 'this tracker')}’?") == QMessageBox.StandardButton.Yes:
            self.state["manual"].remove(tracker); self.save(); self.render()

    def guide(self):
        dialog = QDialog(self); dialog.setWindowTitle("Usage Garden · Field guide"); dialog.resize(560, 630)
        layout = QVBoxLayout(dialog); text = QTextBrowser(); text.setOpenExternalLinks(True)
        text.setHtml("<h2>A field guide to your usage</h2><p>Hover over a number for a quick definition. This guide is also available with F1.</p>" +
            "".join(f"<h3>{term}</h3><p>{definition}</p>" for term, definition in TERMS.items()) +
            f'<hr><p>Documentation checked September 12, 2026. Account readings take precedence over general examples.</p><p><a href="{DOCS_PRICING}">Official pricing and usage guidance</a><br><a href="{DOCS_PROTOCOL}">Official account interface documentation</a></p>' +
            f"<p>Usage Garden · {CODENAME} {__version__}<br>An independent utility; not an official OpenAI product.</p>")
        layout.addWidget(text); layout.addWidget(button("Close", dialog.accept)); dialog.exec()

    def export_history(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export recorded allowance readings", "usage-garden-readings.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            with Path(path).open("w", newline="", encoding="utf-8-sig") as stream:
                writer = csv.writer(stream); writer.writerow(["observed_utc", "bucket", "window", "used_percent", "remaining_percent", "reset_utc"])
                for reading in self.state["history"]:
                    observed = timestamp(reading.get("observed_at"))
                    for window in windows(reading.get("limits", {})):
                        # Prevent formula interpretation when a service-supplied label is opened in Excel.
                        safe_bucket = "'" + window.bucket if window.bucket.startswith(("=", "+", "-", "@")) else window.bucket
                        writer.writerow([observed.isoformat() if observed else "", safe_bucket, window.label,
                                         window.used, window.remaining, window.reset.isoformat() if window.reset else ""])
        except OSError:
            QMessageBox.warning(self, "Export could not be saved", "Choose a writable folder and try again.")

    def restore_window(self):
        self.showNormal(); self.raise_(); self.activateWindow()

    def quit_app(self):
        self.quitting = True; self.close()

    def closeEvent(self, event):
        # The close button exits; normal minimization keeps the tray available.
        self.cancel_work()
        if self.worker and self.worker.isRunning():
            event.ignore(); self.quitting = True
            QTimer.singleShot(200, self.quit_app)
            return
        self.poll_timer.stop(); self.tick_timer.stop(); self.tray.hide(); self.save(); event.accept()

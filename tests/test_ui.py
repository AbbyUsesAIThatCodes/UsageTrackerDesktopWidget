import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import tempfile
import unittest
from PySide6.QtWidgets import QApplication, QLabel
from usage_garden.storage import Store
from usage_garden.ui import GardenWindow, Settings, ManualEditor
from usage_garden.art import THEMES, FLOWERS, PATTERNS
from usage_garden.content import demo_snapshot

app = QApplication.instance() or QApplication([])


class UiTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.store = Store(self.directory.name)
        self.window = GardenWindow(self.store, demo=True, offline=True)
        self.window.show(); app.processEvents()

    def tearDown(self):
        self.window.quit_app(); app.processEvents(); self.directory.cleanup()

    def test_preview_is_explicit_and_never_saved_as_account(self):
        self.assertIn("SAMPLE", self.window.status.text())
        self.assertIsNone(self.store.state["snapshot"])
        self.window.toggle_demo(); app.processEvents()
        self.assertEqual(self.window.status.text(), "Not connected")

    def test_all_palettes_and_flower_choices_render(self):
        for index, theme in enumerate(THEMES):
            self.store.state.update(theme=theme, flower=FLOWERS[index % len(FLOWERS)], pattern=PATTERNS[index % len(PATTERNS)])
            self.window.apply_theme(); self.window.render(); app.processEvents()
            self.assertFalse(self.window.grab().isNull())

    def test_expired_reading_remains_explicit(self):
        snapshot = demo_snapshot()
        snapshot["limits"]["rateLimitsByLimitId"]["codex"]["primary"]["resetsAt"] = 1
        self.store.state["snapshot"] = snapshot
        self.window.demo = False; self.window.render(); app.processEvents()
        texts = [widget.text() for widget in self.window.findChildren(QLabel)]
        self.assertTrue(any("awaiting reading" in text for text in texts))
        self.assertTrue(any("at last reading" in text for text in texts))

    def test_manual_edits_persist_and_do_not_modify_live_snapshot(self):
        self.window.demo = False
        snapshot = demo_snapshot(); self.store.state["snapshot"] = snapshot
        tracker = {"id": "test", "name": "Research", "used": 3, "cap": 10, "units": "tasks", "reset": 1}
        self.store.state["manual"].append(tracker); self.window.increment(tracker)
        self.assertEqual(Store(self.directory.name).state["manual"][0]["used"], 4)
        self.assertEqual(self.store.state["snapshot"], snapshot)

    def test_settings_and_manual_dialogs(self):
        settings = Settings(self.store.state, self.window)
        settings.controls["theme"].setCurrentText("Sage")
        self.assertEqual(settings.values()["theme"], "Sage")
        editor = ManualEditor(None, self.window); editor.name.setText("Research")
        editor.has_reset.setChecked(False)
        self.assertIsNone(editor.value()["reset"])
        settings.close(); editor.close()


if __name__ == "__main__":
    unittest.main()

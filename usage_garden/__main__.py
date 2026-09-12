import argparse
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description="Usage Garden · First Bloom 0.1.0")
    parser.add_argument("--demo", action="store_true", help="Clearly labeled sample readings; no account connection")
    parser.add_argument("--offline", action="store_true", help="Do not connect to Codex")
    parser.add_argument("--data-dir", type=Path, help="Override the local settings directory")
    parser.add_argument("--screenshot", type=Path, help="Render an offscreen preview and exit")
    args = parser.parse_args()
    # Qt's offscreen Windows backend lacks the normal system font database.
    # Grab the native window on Windows; use offscreen rendering on Linux CI.
    if args.screenshot and sys.platform != "win32":
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtCore import QTimer, QLockFile
    from PySide6.QtWidgets import QApplication, QMessageBox
    from .storage import Store
    from .ui import GardenWindow
    app = QApplication(sys.argv[:1]); app.setApplicationName("Usage Garden"); app.setOrganizationName("UsageGarden")
    store = Store(args.data_dir)
    store.directory.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(store.directory / "usage-garden.lock"))
    if not lock.tryLock(0):
        QMessageBox.information(None, "Usage Garden is already open", "Find Usage Garden in your taskbar or system tray.")
        return 0
    window = GardenWindow(store, args.demo, args.offline or bool(args.screenshot)); window.show()
    if args.screenshot:
        def capture():
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            saved = window.grab().save(str(args.screenshot))
            window.quit_app(); app.exit(0 if saved else 1)
        QTimer.singleShot(300, capture)
    result = app.exec(); lock.unlock(); return result


if __name__ == "__main__":
    raise SystemExit(main())

"""Atomic local settings; a damaged file is preserved for recovery."""
import json
import os
from pathlib import Path
import tempfile
from .model import now_utc


def default_state():
    return {"schema": 1, "theme": "Rosewater", "flower": "Cosmos", "pattern": "Meadow",
            "always_on_top": False, "compact": False, "refresh_seconds": 300,
            "codex_path": "", "snapshot": None, "manual": [], "history": []}


def state_directory():
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "UsageGarden"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "UsageGarden"


class Store:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory else state_directory()
        self.path = self.directory / "settings.json"
        self.warning = ""
        self.state = default_state()
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(raw, dict) or raw.get("schema") != 1:
                    raise ValueError("Unsupported settings format")
                if not all(isinstance(raw.get(key, []), list) for key in ("manual", "history")):
                    raise ValueError("Invalid saved lists")
                for key in ("theme", "flower", "pattern", "codex_path"):
                    if key in raw and not isinstance(raw[key], str):
                        raise ValueError("Invalid saved setting")
                if raw.get("snapshot") is not None and not isinstance(raw["snapshot"], dict):
                    raise ValueError("Invalid snapshot")
                self.state.update(raw)
            except (ValueError, OSError, TypeError):
                backup = self.path.with_name(f"settings-unreadable-{now_utc():%Y%m%d-%H%M%S}.json")
                try:
                    self.path.rename(backup)
                    self.warning = "Saved settings could not be read. The original was kept beside the new settings."
                except OSError:
                    self.warning = "Saved settings could not be read or moved. Changes will not be saved this session."
                    self.path = None

    def save(self):
        if self.path is None:
            raise OSError("Original settings are protected; choose a writable data folder.")
        self.directory.mkdir(parents=True, exist_ok=True)
        self.state["history"] = self.state["history"][-500:]
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.directory,
                                         prefix="settings-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            try:
                json.dump(self.state, stream, indent=2, ensure_ascii=False, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            except Exception:
                temporary.unlink(missing_ok=True)
                raise
        try:
            os.replace(temporary, self.path)
        finally:
            temporary.unlink(missing_ok=True)

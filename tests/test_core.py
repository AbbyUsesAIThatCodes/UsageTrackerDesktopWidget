from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from usage_garden.model import windows, number, timestamp, sanitize_limits, manual_remaining
from usage_garden.storage import Store
from usage_garden.provider import read_account, RpcClient, ProviderError, safe_auth_url


class ModelTests(unittest.TestCase):
    def test_unknown_is_not_zero(self):
        reading = {"rateLimits": {"primary": {"usedPercent": None}}}
        window = windows(reading)[0]
        self.assertIsNone(window.remaining)
        self.assertEqual(window.countdown(datetime.now(timezone.utc)), "Reset time not reported")
        for value in [True, "25", float("nan"), float("inf")]:
            self.assertIsNone(number(value))

    def test_dynamic_windows_and_multiple_buckets(self):
        reading = {"rateLimitsByLimitId": {"codex": {"primary": {"usedPercent": 28, "windowDurationMins": 300},
            "secondary": {"usedPercent": 75, "windowDurationMins": 10080}},
            "extra": {"limitName": "Special model", "primary": {"usedPercent": 8, "windowDurationMins": 60}}}}
        result = windows(reading)
        self.assertEqual(len(result), 3)
        self.assertEqual([item.remaining for item in result], [72, 25, 92])
        self.assertEqual(result[2].label, "1-hour allowance")
        self.assertEqual(result[1].label, "Weekly allowance")

    def test_reset_never_invents_a_refill(self):
        now = datetime.now(timezone.utc)
        window = windows({"rateLimits": {"primary": {"usedPercent": 100, "resetsAt": (now - timedelta(seconds=1)).timestamp()}}})[0]
        self.assertTrue(window.expired(now)); self.assertEqual(window.remaining, 0)
        self.assertIn("awaiting", window.countdown(now))

    def test_percent_overage_and_invalid_timestamp(self):
        self.assertEqual(windows({"rateLimits": {"primary": {"usedPercent": 103}}})[0].remaining, 0)
        self.assertIsNone(timestamp(1e100))
        self.assertIsNone(timestamp(-1))

    def test_empty_multiview_falls_back(self):
        self.assertEqual(len(windows({"rateLimitsByLimitId": {}, "rateLimits": {"primary": {"usedPercent": 5}}})), 1)

    def test_earned_reset_count_is_authoritative(self):
        clean = sanitize_limits({"rateLimitResetCredits": {"availableCount": 8, "credits": [{"id": "secret", "expiresAt": 1900000000}]}})
        self.assertEqual(clean["rateLimitResetCredits"]["availableCount"], 8)
        self.assertNotIn("secret", json.dumps(clean))

    def test_manual_allowance_is_never_automatically_reset(self):
        tracker = {"used": 20, "cap": 10, "reset": 1}
        self.assertEqual(manual_remaining(tracker), 0)
        self.assertEqual(tracker["used"], 20)
        self.assertIsNone(manual_remaining({"cap": 0, "used": 0}))


class StorageTests(unittest.TestCase):
    def test_persistence_and_bounded_history(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory); store.state["theme"] = "Sage"
            store.state["history"] = [{"observed_at": i} for i in range(600)]; store.save()
            restored = Store(directory)
            self.assertEqual(restored.state["theme"], "Sage"); self.assertEqual(len(restored.state["history"]), 500)
            self.assertFalse(list(Path(directory).glob("*.tmp")))

    def test_corrupt_file_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "settings.json").write_text("broken", encoding="utf-8")
            store = Store(directory); self.assertTrue(store.warning); store.save()
            self.assertEqual(list(Path(directory).glob("settings-unreadable*.json"))[0].read_text(), "broken")


class ProtocolTests(unittest.TestCase):
    def command(self, mode="normal"):
        return [sys.executable, str(Path(__file__).with_name("fake_codex.py")), mode]

    def test_full_read_handshake_and_no_private_fields_saved(self):
        reading = read_account(command=self.command())
        self.assertEqual(windows(reading["limits"])[0].remaining, 75)
        self.assertEqual(reading["activity"]["summary"]["lifetimeTokens"], 12345)
        self.assertNotIn("private@example", json.dumps(reading)); self.assertNotIn("never-persist", json.dumps(reading))

    def test_optional_unsupported_activity_keeps_limits(self):
        reading = read_account(command=self.command("old-version"))
        self.assertTrue(reading["activity_error"]); self.assertTrue(windows(reading["limits"]))

    def test_signed_out_and_api_auth(self):
        for mode in ("signed-out", "api"):
            with self.subTest(mode=mode), self.assertRaises(ProviderError):
                read_account(command=self.command(mode))

    def test_login_notification_before_response(self):
        links = []
        result = read_account(sign_in=True, open_url=links.append, command=self.command())
        self.assertEqual(len(links), 1); self.assertEqual(result["plan"], "pro")

    def test_only_official_https_login_addresses(self):
        self.assertTrue(safe_auth_url("https://chatgpt.com/auth"))
        for url in ("http://chatgpt.com/auth", "https://chatgpt.com.evil.test", "file:///etc/passwd", "https://user@chatgpt.com", "https://chatgpt.com:1234/auth"):
            self.assertFalse(safe_auth_url(url))

    def test_timeout_and_cancel_clean_up_process(self):
        client = RpcClient(self.command("hang"))
        start = time.monotonic()
        try:
            with self.assertRaises(ProviderError):
                client.request("initialize", {}, timeout=.15)
        finally:
            client.close()
        self.assertIsNotNone(client.process.poll()); self.assertLess(time.monotonic() - start, 3)
        event = threading.Event(); event.set(); client = RpcClient(self.command(), event)
        try:
            with self.assertRaises(ProviderError):
                client.initialize()
        finally:
            client.close()


if __name__ == "__main__":
    unittest.main()

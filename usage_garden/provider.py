"""Documented Codex stdio RPC. No model turns, browser cookies, or private endpoints."""
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import time
from urllib.parse import urlparse
from . import __version__
from .model import now_utc, sanitize_limits, sanitize_activity


class ProviderError(Exception):
    pass


class RpcError(ProviderError):
    def __init__(self, method, code):
        self.code = code
        super().__init__(f"Codex could not complete {method} (code {code}). Try signing in again or updating Codex.")


def executable(configured=""):
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_file() and (os.name != "nt" or candidate.suffix.lower() == ".exe"):
            return str(candidate.resolve())
        raise ProviderError("The selected Codex executable is missing. Choose codex.exe in Appearance & connection.")
    root = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
    bundled = root / "vendor" / ("codex.exe" if os.name == "nt" else "codex")
    if bundled.is_file():
        return str(bundled)
    found = shutil.which("codex.exe" if os.name == "nt" else "codex")
    if found:
        return found
    # npm uses a .cmd shim on Windows. Locate its native binary, never run a shell shim.
    if os.name == "nt":
        npm = Path(os.environ.get("APPDATA", "")) / "npm/node_modules/@openai"
        for package in (npm / "codex", npm / "codex/node_modules/@openai/codex-win32-x64",
                        npm / "codex/node_modules/@openai/codex-win32-arm64"):
            for candidate in package.glob("vendor/*/codex/codex.exe"):
                return str(candidate)
    raise ProviderError("Codex was not found. Use the Windows download with Codex included, or choose codex.exe in Appearance & connection.")


def safe_auth_url(url):
    try:
        parsed = urlparse(url)
        return (parsed.scheme == "https" and parsed.hostname in ("chatgpt.com", "auth.openai.com", "auth0.openai.com")
                and parsed.username is None and parsed.password is None and parsed.port in (None, 443))
    except (ValueError, TypeError):
        return False


class RpcClient:
    def __init__(self, command, cancel=None):
        self.cancel = cancel or threading.Event()
        self.messages = queue.Queue(maxsize=1000)
        self.pending_notifications = []
        self.sequence = 0
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        # Inherited auth stays inside Codex. Its stderr is intentionally not logged.
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                                        errors="replace", bufsize=1, creationflags=flags)
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self):
        try:
            for line in self.process.stdout:
                if len(line) > 2_000_000:
                    continue
                try:
                    value = json.loads(line)
                except ValueError:
                    continue
                if isinstance(value, dict):
                    try:
                        self.messages.put(value, timeout=0.5)
                    except queue.Full:
                        break
        finally:
            try:
                self.messages.put(None, timeout=0.5)
            except queue.Full:
                pass

    def send(self, message):
        try:
            self.process.stdin.write(json.dumps(message) + "\n")
            self.process.stdin.flush()
        except (OSError, ValueError):
            raise ProviderError("Codex closed the connection. Check its version and try again.") from None

    def receive(self, deadline):
        while time.monotonic() < deadline:
            if self.cancel.is_set():
                raise ProviderError("Connection cancelled.")
            try:
                message = self.messages.get(timeout=min(0.2, max(0.01, deadline - time.monotonic())))
            except queue.Empty:
                continue
            if message is None:
                raise ProviderError("Codex exited before returning a reading. Check the selected executable.")
            if "method" in message and "id" in message:
                self.send({"id": message["id"], "error": {"code": -32601, "message": "Read-only usage client"}})
                continue
            return message
        raise ProviderError("Codex did not respond in time. Check your connection and try Refresh.")

    def request(self, method, params=None, timeout=20):
        self.sequence += 1
        identifier = self.sequence
        message = {"id": identifier, "method": method}
        if params is not None:
            message["params"] = params
        self.send(message)
        deadline = time.monotonic() + timeout
        while True:
            reply = self.receive(deadline)
            if reply.get("id") == identifier:
                if "error" in reply:
                    error = reply["error"]
                    raise RpcError(method, error.get("code", "unknown") if isinstance(error, dict) else "unknown")
                result = reply.get("result")
                if not isinstance(result, dict):
                    raise ProviderError("Codex returned an unrecognized response. Update Codex and retry.")
                return result
            if reply.get("method") == "account/login/completed":
                self.pending_notifications.append(reply)

    def initialize(self):
        self.request("initialize", {"clientInfo": {"name": "usage_garden", "title": "Usage Garden", "version": __version__}})
        self.send({"method": "initialized", "params": {}})

    def sign_in(self, open_url):
        result = self.request("account/login/start", {"type": "chatgpt"})
        url = result.get("authUrl", "")
        if not safe_auth_url(url):
            raise ProviderError("Codex returned an unexpected sign-in address. Sign in using the official Codex app instead.")
        open_url(url)
        deadline = time.monotonic() + 180
        while True:
            message = self.pending_notifications.pop(0) if self.pending_notifications else self.receive(deadline)
            if message.get("method") == "account/login/completed":
                params = message.get("params", {})
                if params.get("loginId") not in (None, result.get("loginId")):
                    continue
                if params.get("success") is True:
                    return
                raise ProviderError("Sign-in was not completed. You can try again whenever you are ready.")

    def close(self):
        try:
            self.process.stdin.close()
            self.process.wait(timeout=1)
        except (OSError, subprocess.TimeoutExpired):
            self.process.terminate()
            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)
        self.reader.join(timeout=1)
        self.process.stdout.close()


def read_account(path="", sign_in=False, open_url=lambda url: None, cancel=None, command=None):
    client = RpcClient(command or [executable(path), "app-server"], cancel)
    try:
        client.initialize()
        if sign_in:
            client.sign_in(open_url)
        account = client.request("account/read", {"refreshToken": False}).get("account")
        if not isinstance(account, dict):
            raise ProviderError("Connect your ChatGPT account to see live readings. Choose Sign in.")
        if account.get("type") in ("apiKey", "amazonBedrock"):
            raise ProviderError("Codex is using API or Bedrock billing. Sign in with ChatGPT to read subscription allowances.")
        limits = client.request("account/rateLimits/read")
        activity_error = ""
        try:
            activity = sanitize_activity(client.request("account/usage/read", timeout=12))
        except ProviderError:
            activity = {}
            activity_error = "Token activity was not available from this account or Codex version. Allowance readings are still shown."
        return {"observed_at": now_utc().timestamp(), "plan": str(account.get("planType") or "Not reported"),
                "limits": sanitize_limits(limits), "activity": activity, "activity_error": activity_error}
    finally:
        client.close()

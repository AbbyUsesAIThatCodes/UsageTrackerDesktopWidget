"""Deterministic stdio peer; contains only fictional account readings."""
import json
import sys
import time

mode = sys.argv[1] if len(sys.argv) > 1 else "normal"
initialized = False


def send(value):
    print(json.dumps(value), flush=True)


for line in sys.stdin:
    request = json.loads(line); method = request["method"]
    if mode == "hang":
        time.sleep(3)
        continue
    if method == "initialize":
        send({"id": request["id"], "result": {"userAgent": "fake"}})
    elif method == "initialized":
        initialized = True
    elif not initialized:
        send({"id": request["id"], "error": {"code": -32000}})
    elif method == "account/read":
        account = None if mode == "signed-out" else {"type": "apiKey"} if mode == "api" else {"type": "chatgpt", "email": "private@example.test", "planType": "pro"}
        send({"method": "account/updated", "params": {"planType": "pro"}})
        send({"id": request["id"], "result": {"account": account}})
    elif method == "account/rateLimits/read":
        send({"id": request["id"], "result": {"rateLimits": {"limitId": "codex",
            "primary": {"usedPercent": 25, "windowDurationMins": 300, "resetsAt": 1900000000},
            "secondary": None, "secret": "never-persist"},
            "rateLimitResetCredits": {"availableCount": 2, "credits": [{"id": "never-persist", "expiresAt": 1900000000}]}}})
    elif method == "account/usage/read":
        if mode == "old-version":
            send({"id": request["id"], "error": {"code": -32601}})
        else:
            send({"id": request["id"], "result": {"summary": {"lifetimeTokens": 12345, "peakDailyTokens": None}, "dailyUsageBuckets": None}})
    elif method == "account/login/start":
        # Notification may arrive before the response: the client must not lose it.
        send({"method": "account/login/completed", "params": {"loginId": "sample", "success": True}})
        send({"id": request["id"], "result": {"loginId": "sample", "authUrl": "https://chatgpt.com/auth/sample"}})
    else:
        send({"id": request.get("id"), "error": {"code": -32601}})

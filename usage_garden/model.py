"""Service data is a timestamped observation, never an inferred entitlement."""
from dataclasses import dataclass
from datetime import datetime, timezone
import math


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def timestamp(value):
    value = number(value)
    if value is None or value < 0:
        return None
    try:
        return datetime.fromtimestamp(value, timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def now_utc():
    return datetime.now(timezone.utc)


def duration(seconds):
    minutes = max(1, math.ceil(seconds / 60))
    days, minutes = divmod(minutes, 1440)
    hours, minutes = divmod(minutes, 60)
    return " ".join(part for part in (
        f"{days}d" if days else "", f"{hours}h" if hours else "",
        f"{minutes}m" if minutes else "") if part) or "<1m"


def window_name(minutes, fallback):
    if minutes is None or minutes <= 0:
        return fallback
    if minutes == 10080:
        return "Weekly allowance"
    if minutes % 1440 == 0:
        return f"{minutes / 1440:g}-day allowance"
    if minutes % 60 == 0:
        return f"{minutes / 60:g}-hour allowance"
    return f"{minutes:g}-minute allowance"


@dataclass(frozen=True)
class Window:
    bucket: str
    name: str
    label: str
    used: float | None
    minutes: float | None
    reset: datetime | None
    reached: str | None = None

    @property
    def remaining(self):
        return None if self.used is None else max(0, 100 - self.used)

    def expired(self, now):
        return self.reset is not None and self.reset <= now

    def countdown(self, now):
        if self.reset is None:
            return "Reset time not reported"
        if self.expired(now):
            return "Reset due · awaiting reading"
        return f"Resets in {duration((self.reset - now).total_seconds())}"


def buckets(result):
    if not isinstance(result, dict):
        return []
    multi = result.get("rateLimitsByLimitId")
    if isinstance(multi, dict) and multi:
        return [(str(key), value) for key, value in multi.items() if isinstance(value, dict)]
    single = result.get("rateLimits")
    return [(str(single.get("limitId") or "codex"), single)] if isinstance(single, dict) else []


def windows(result):
    output = []
    for bucket, value in buckets(result):
        name = value.get("limitName") or ("ChatGPT Work + Codex" if bucket == "codex" else bucket)
        for key, fallback in (("primary", "Primary allowance"), ("secondary", "Secondary allowance")):
            raw = value.get(key)
            if not isinstance(raw, dict):
                continue
            used = number(raw.get("usedPercent"))
            # A service can report over 100%; preserve it and clamp only the gauge.
            if used is not None and used < 0:
                used = None
            minutes = number(raw.get("windowDurationMins"))
            output.append(Window(bucket, str(name), window_name(minutes, fallback), used,
                                 minutes, timestamp(raw.get("resetsAt")), value.get("rateLimitReachedType")))
    return output


def sanitize_limits(result):
    """Only persist fields we display; no tokens, email, raw RPC, or opaque reset IDs."""
    clean = {"rateLimitsByLimitId": {}}
    for key, bucket in buckets(result):
        entry = {field: bucket.get(field) for field in ("limitId", "limitName", "planType", "rateLimitReachedType")
                 if isinstance(bucket.get(field), (str, type(None)))}
        for field in ("primary", "secondary"):
            window = bucket.get(field)
            if isinstance(window, dict):
                entry[field] = {name: number(window.get(name)) for name in
                                ("usedPercent", "windowDurationMins", "resetsAt")}
        credits = bucket.get("credits")
        if isinstance(credits, dict):
            entry["credits"] = {name: credits[name] for name in ("hasCredits", "unlimited", "balance")
                                if isinstance(credits.get(name), (str, bool, int, float))}
        clean["rateLimitsByLimitId"][key] = entry
    resets = result.get("rateLimitResetCredits")
    if isinstance(resets, dict):
        clean["rateLimitResetCredits"] = {"availableCount": number(resets.get("availableCount"))}
        if isinstance(resets.get("credits"), list):
            clean["rateLimitResetCredits"]["credits"] = [
                {field: row.get(field) for field in ("expiresAt", "title", "description", "status")}
                for row in resets["credits"] if isinstance(row, dict)]
    return clean


def sanitize_activity(result):
    summary = result.get("summary") if isinstance(result, dict) else None
    clean = {"summary": {key: number(summary.get(key)) for key in (
        "lifetimeTokens", "peakDailyTokens", "longestRunningTurnSec", "currentStreakDays", "longestStreakDays")}
        if isinstance(summary, dict) else {}}
    daily = result.get("dailyUsageBuckets") if isinstance(result, dict) else None
    if isinstance(daily, list):
        clean["dailyUsageBuckets"] = [{"startDate": str(row.get("startDate", ""))[:10],
                                        "tokens": number(row.get("tokens"))}
                                       for row in daily if isinstance(row, dict)][-366:]
    return clean


def manual_remaining(tracker):
    cap, used = number(tracker.get("cap")), number(tracker.get("used"))
    if cap is None or cap <= 0 or used is None or used < 0:
        return None
    return max(0, cap - used)

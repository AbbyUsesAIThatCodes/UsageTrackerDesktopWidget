DOCS_PRICING = "https://developers.openai.com/codex/pricing"
DOCS_PROTOCOL = "https://learn.chatgpt.com/docs/app-server"
DASHBOARD = "https://chatgpt.com/codex/settings/usage"
TERMS = {
    "Allowance": "The amount of included work available within a usage window. ChatGPT Work and Codex share usage. Work varies in cost, so a percentage is not a fixed number of messages.",
    "Remaining": "100% minus the service's reported used percentage, with a minimum of zero. This is a reading at the displayed time. It is not a forecast of how many tasks will fit.",
    "Usage window": "A period over which an allowance is measured. The widget uses the duration returned by the service, rather than assuming every account has the same five-hour or weekly cap. Multiple windows can apply at once.",
    "Reset": "The next reset timestamp reported by the service, displayed in your computer's time zone. A reset applies to its own window. Reaching the time does not prove your allowance refilled; the widget waits for a new reading.",
    "Refresh": "Ask the account service for a new reading. Refreshing this widget does not refill your allowance, consume an earned reset, or start an AI task. The countdown updates locally between readings.",
    "Credits": "A credit balance returned by the service for a bucket. Credits are distinct from included allowances and earned resets. They are not dollars or tokens; this widget does not infer a money conversion or purchase anything.",
    "Earned resets": "Banked resets reported as available by the service. These are separate from ordinary timed resets and paid credits. Some expire. Usage Garden only displays them; use the official dashboard to review or redeem them.",
    "Tokens": "Units of model input and output. Instructions, conversation context, tool results, and responses can all use tokens. A token is often a piece of a word. Token totals are activity, not an exact measure of subscription allowance or dollars.",
    "Lifetime tokens": "The lifetime token-activity total returned by the account service. The service defines its scope; this is not guaranteed to include every interaction across every ChatGPT feature.",
    "Peak daily tokens": "The largest daily token-activity total returned by the account service. A busy day is not necessarily the most expensive day: model choice and input/output mix also matter.",
    "Longest turn": "The duration of the longest running turn reported by the account service. A turn includes the work done in response to one request, which may involve many tools and model calls.",
    "Streak": "Consecutive activity days as defined by the account service. It is a descriptive statistic, not a target or an indication that you should use more.",
    "Cached reading": "A reading saved from an earlier successful refresh. It can be useful offline, but may no longer match your account. The widget always displays when it was observed.",
    "Not reported": "The service did not supply a usable value. Missing information is neither zero nor unlimited. Features, accounts, plans, and Codex versions may expose different data.",
    "Manual tracker": "Numbers you record yourself for a limit shown elsewhere, such as a ChatGPT model or research tool. They are never automatically measured. A countdown is a reminder; only a new observation confirms a reset.",
    "Context window": "How much information a model can work with at once. It is different from your account's usage allowance. Longer conversations may increase usage, but context size is not a remaining-message counter.",
    "API billing": "Direct OpenAI API usage has separate billing and rate limits. An API key does not turn this widget into a ChatGPT subscription tracker. This version connects through your ChatGPT sign-in in Codex.",
    "Plan": "The plan name reported by the connected account. A generic name such as Pro may not identify its exact tier, so the widget does not guess a price or multiplier.",
    "Usage bucket": "A named allowance or special limit returned by the service. The widget displays every reported bucket separately so different allowances are not accidentally added together.",
}


def demo_snapshot():
    from .model import now_utc
    from datetime import timedelta
    now = now_utc()
    return {"observed_at": now.timestamp(), "plan": "Pro · sample", "activity_error": "", "limits": {
        "rateLimitsByLimitId": {"codex": {"limitId": "codex", "limitName": "ChatGPT Work + Codex",
            "primary": {"usedPercent": 28, "windowDurationMins": 300, "resetsAt": (now + timedelta(hours=2, minutes=14)).timestamp()},
            "secondary": {"usedPercent": 46, "windowDurationMins": 10080, "resetsAt": (now + timedelta(days=3, hours=8)).timestamp()},
            "credits": {"hasCredits": True, "unlimited": False, "balance": "125"}}},
        "rateLimitResetCredits": {"availableCount": 2}},
        "activity": {"summary": {"lifetimeTokens": 1834250, "peakDailyTokens": 124810,
            "longestRunningTurnSec": 932, "currentStreakDays": 4, "longestStreakDays": 12},
            "dailyUsageBuckets": [{"startDate": (now - timedelta(days=13-index)).strftime("%Y-%m-%d"), "tokens": value}
                for index, value in enumerate([31000, 24000, 51000, 19000, 88000, 42000, 36000, 66000, 17000, 52000, 74000, 38000, 93000, 61000])]}}

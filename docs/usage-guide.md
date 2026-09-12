# Understanding your usage

Think of the widget as a set of separate gauges, each with its own source and timestamp.

| Term | What it means for you |
| --- | --- |
| Included allowance | Your plan's available work within a period. It is not a fixed message count: model, context, tools, reasoning, and caching affect usage. |
| Five-hour or weekly window | A period over which usage is limited, when the account reports it. Multiple windows can constrain the same work. The app uses the actual returned duration. |
| Refresh | Obtain a new reading. It does not restore the allowance. |
| Reset | A reported time when a particular usage window is expected to reset. It does not necessarily reset another window or restore paid credits. |
| Earned reset | A banked reset available for eligible use, with an expiry when reported. It is separate from the ordinary countdown. The widget displays these but does not redeem them. |
| Credits | A separate balance used for eligible work. Credits are not dollars or tokens, and their availability does not make every feature unlimited. |
| Tokens | Units of input/output activity. A longer task can use many internal calls and tool results. Token count alone does not establish the exact allowance consumed. |
| Context window | How much information the model can work with at once. It is different from an account's quota window. |
| Cached | The last successful observation, which may no longer describe your account. |
| Not reported | There is no usable value from the service. It does not mean zero, free, or unlimited. |

OpenAI's current documentation says **Work and Codex share usage**, including local and cloud work. Weekly limits may also apply. Its published message ranges are estimates rather than fixed message quotas. Check the [official account dashboard](https://chatgpt.com/codex/settings/usage) for the entitlements and notices currently applying to your account.

For quick questions and short rewrites, ordinary Chat can be a useful fit. For substantial tasks and finished files, Work is designed to carry out multiple steps. Choose a lighter available model for routine tasks when it meets your needs. Specifying the intended outcome, sources, and stopping point can help keep a task focused. These choices affect usage, but the widget does not pretend to predict an exact saving.

## Limits of this first version

The supported Codex interface provides usage-window observations and optional account activity. It does not establish a complete API for every ordinary ChatGPT feature counter. Use a manual tracker for a number shown elsewhere. The widget does not read your chat contents or infer how many prompts you sent. It also does not report direct API billing, per-task cost attribution, or speculative exact “messages remaining.”

Account and workspace selection follow Codex's signed-in account. A generic `pro` label does not distinguish all Pro tiers. Make sure the official dashboard and the account used for sign-in match the one you intend to monitor. The application avoids storing account email addresses; it shows the reported plan and reading times.

The widget keeps every returned allowance bucket separate. It does not add together percentages, sum duplicate credit balances, or substitute one account metric for another. When a reset countdown reaches its timestamp, it keeps the old observation explicitly labeled until the next refresh.

## Sources

Read September 12, 2026:

- [OpenAI pricing and usage guidance](https://developers.openai.com/codex/pricing): shared Work/Codex allowance, variable usage, window estimates, credits, and the dashboard.
- [OpenAI app-server documentation](https://learn.chatgpt.com/docs/app-server): `initialize`, `account/read`, browser login, `account/rateLimits/read`, optional reset credits, and `account/usage/read`.
- [Get started with ChatGPT Work](https://learn.chatgpt.com/docs/get-started-with-work): choosing Chat or Work and using Work efficiently.

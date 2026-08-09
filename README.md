# AI News Content Radar

A zero-cost, GitHub Actions-friendly personal AI news radar. It collects official AI news feeds/pages and free discovery sources, groups related items into story events, scores them, and sends an hourly Telegram digest plus one-time breakout alerts.

## Setup

1. Create a **private** GitHub repository and add these Actions secrets:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
2. Review `config/sources.json` and adjust source URLs, keywords, and source tiers.
3. Enable Actions. The scheduler runs hourly at minute 17 UTC; use **Run workflow** for the first test.

The initial state file is committed intentionally: GitHub Actions updates it to remember processed URLs, current events, and sent Telegram notifications. Do not put credentials in it.

## Local run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:TELEGRAM_BOT_TOKEN = '...'
$env:TELEGRAM_CHAT_ID = '...'
python -m app.main --dry-run
```

Remove `--dry-run` only after configuring Telegram secrets. `--x-enabled` additionally requires a dedicated X account cookie secret and is disabled by default.

## Guardrails

- X is optional. A Twikit failure never blocks RSS/web/news collection.
- The project does not bypass CAPTCHAs, paywalls, protections, or rate limits.
- Feed/page collection is deliberately small and polite. Non-RSS pages emit only linked article candidates; pages that cannot expose them safely return no candidates. Check each publisher's terms before enabling a source.
- OpenRouter is intentionally not included: extractive summaries are free and reliable. It can be added later behind a feature flag.

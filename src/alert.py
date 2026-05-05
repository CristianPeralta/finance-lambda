"""
alert.py — Lambda finance-alert  [Phase 2 — not yet implemented]
Trigger: EventBridge cron daily 8pm Peru (01:00 UTC)

Compares current month spending against hardcoded budgets.
Sends a Telegram alert if spending exceeds 80%.

Budget env vars:
  BUDGET_PAREJA  — default 3000
  BUDGET_MANTYS  — default 500
"""

import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    # TODO Phase 2: read Google Sheets, compare vs budget, alert if > 80%
    logger.info("finance-alert triggered (Phase 2 pending)")
    return {"statusCode": 200, "body": "alert stub"}

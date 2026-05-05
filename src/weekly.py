"""
weekly.py — Lambda finance-weekly  [Phase 2 — not yet implemented]
Trigger: EventBridge cron Monday 8am Peru (13:00 UTC)

Generates a weekly summary for MANTYS and Pareja and sends it to Telegram.
"""

import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    # TODO Phase 2: read Google Sheets, build weekly summary, send to Telegram
    logger.info("finance-weekly triggered (Phase 2 pending)")
    return {"statusCode": 200, "body": "weekly stub"}

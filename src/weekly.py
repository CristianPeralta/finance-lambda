"""
weekly.py — Lambda finance-weekly  [FASE 2 — pendiente implementar]
Trigger: EventBridge cron lunes 8am Peru (13:00 UTC)

Genera resumen semanal de MANTYS y Pareja y lo manda a Telegram.
"""

import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    # TODO Fase 2: leer Google Sheets, generar resumen semanal, enviar a Telegram
    logger.info("finance-weekly triggered (Fase 2 pendiente)")
    return {"statusCode": 200, "body": "weekly stub"}

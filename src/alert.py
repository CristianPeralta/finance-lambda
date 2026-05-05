"""
alert.py — Lambda finance-alert  [FASE 2 — pendiente implementar]
Trigger: EventBridge cron diario 8pm Peru (01:00 UTC)

Compara gastos del mes vs presupuesto hardcodeado.
Si supera 80%, manda alerta a Telegram.

Presupuestos (env vars):
  BUDGET_PAREJA  — default 3000
  BUDGET_MANTYS  — default 500
"""

import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    # TODO Fase 2: leer Google Sheets, comparar vs presupuesto, enviar alerta si > 80%
    logger.info("finance-alert triggered (Fase 2 pendiente)")
    return {"statusCode": 200, "body": "alert stub"}

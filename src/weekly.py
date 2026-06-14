"""
weekly.py — Lambda finance-weekly
Trigger: EventBridge cron Monday 8am Peru (13:00 UTC)

Sends a weekly financial summary to Telegram and refreshes the Resumen sheet.
"""

import logging
from datetime import date

from sheets import get_sheet, get_monthly_summary
from telegram import notify
from update_resumen import update_resumen_sheet

logger = logging.getLogger()
logger.setLevel(logging.INFO)

MESES_ES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def _build_message(data: dict) -> str:
    today = date.today()
    mes   = MESES_ES[today.month]

    lines = [
        f"📊 *Resumen semanal — {mes} {today.year}*\n",
        "🏭 *MANTYS*",
        f"  Ingresos cobrados: S/ {data['mantys_ingresos']:.2f}",
        f"  Gastos:            S/ {data['mantys_gastos']:.2f}",
        f"  Ganancia neta:     S/ {data['mantys_ganancia']:.2f}",
        "",
        "👫 *Pareja*",
        f"  Ingresos: S/ {data['pareja_ingresos']:.2f}",
        f"  Gastos:   S/ {data['pareja_gastos']:.2f}",
        f"  Balance:  S/ {data['pareja_balance']:.2f}",
        "",
        "_Hoja Resumen actualizada_ ✅",
    ]
    return "\n".join(lines)


def lambda_handler(event, context):
    try:
        sh = get_sheet()

        update_resumen_sheet(sh)
        logger.info("Resumen sheet updated")

        data    = get_monthly_summary(sh)
        message = _build_message(data)
        notify(message)
        logger.info("Weekly summary sent")

    except Exception as exc:
        logger.exception("Unhandled error in finance-weekly: %s", exc)

    return {"statusCode": 200, "body": "ok"}

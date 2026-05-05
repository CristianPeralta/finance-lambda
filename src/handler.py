"""
handler.py — Lambda finance-handler
Recibe webhooks de Telegram, parsea mensajes y escribe en Google Sheets.

Trigger: POST /webhook (API Gateway HTTP API)
"""

import json
import logging
import os
from datetime import date

from parser import parse_message
from sheets import get_sheet, append_row, get_monthly_summary
from telegram import reply, send_message

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _format_summary(data: dict, scope_hint: str | None) -> str:
    lines = [f"*Resumen {data['month']}*\n"]

    if scope_hint != "pareja":
        lines += [
            "🏭 *MANTYS*",
            f"  Ingresos cobrados: S/ {data['mantys_ingresos']:.2f}",
            f"  Gastos:            S/ {data['mantys_gastos']:.2f}",
            f"  Ganancia neta:     S/ {data['mantys_ganancia']:.2f}",
        ]

    if scope_hint != "mantys":
        if scope_hint != "pareja":
            lines.append("")
        lines += [
            "👫 *Pareja*",
            f"  Ingresos: S/ {data['pareja_ingresos']:.2f}",
            f"  Gastos:   S/ {data['pareja_gastos']:.2f}",
            f"  Balance:  S/ {data['pareja_balance']:.2f}",
        ]

    return "\n".join(lines)


def _handle_registro(result, update: dict) -> str:
    today = date.today().strftime("%d/%m/%Y")
    sh    = get_sheet()

    if result.tipo == "gasto":
        if result.scope == "mantys":
            append_row(sh, "MANTYS_Gastos", [
                today, result.description, result.category,
                result.amount, result.paid_by, result.raw,
            ])
            return f"✅ Gasto MANTYS: *{result.category}* — S/ {result.amount:.2f} ({result.paid_by})"

        if result.scope == "personal":
            append_row(sh, "Personal_Gastos", [
                today, result.description, result.category,
                result.amount, result.raw,
            ])
            return f"✅ Gasto personal: *{result.category}* — S/ {result.amount:.2f}"

        # pareja (default)
        append_row(sh, "Pareja_Gastos", [
            today, result.description, result.category,
            result.amount, result.paid_by, result.raw,
        ])
        return f"✅ Gasto pareja: *{result.category}* — S/ {result.amount:.2f} ({result.paid_by})"

    # ingreso
    if result.scope == "mantys":
        append_row(sh, "MANTYS_Ingresos", [
            today, result.pedido_num, result.cliente,
            result.description, result.amount, "cobrado", result.raw,
        ])
        label = f"{result.description} ({result.pedido_num})" if result.pedido_num else result.description
        return f"✅ Ingreso MANTYS: {label} — S/ {result.amount:.2f}"

    # ingreso pareja
    fuente = "otro"
    t = result.raw.lower()
    if "sueldo" in t or "salario" in t:
        fuente = "sueldo-cristian" if "cristian" in t else "sueldo-roxsy"
    elif "freelance" in t:
        fuente = "freelance"
    append_row(sh, "Pareja_Ingresos", [
        today, result.description, fuente, result.amount, result.raw,
    ])
    return f"✅ Ingreso pareja: *{fuente}* — S/ {result.amount:.2f}"


def lambda_handler(event, context):
    # Telegram espera siempre 200 — errores internos se reportan al usuario via mensaje
    try:
        body   = json.loads(event.get("body") or "{}")
        update = body

        message_obj = update.get("message", {})
        text        = (message_obj.get("text") or "").strip()
        chat_id     = message_obj.get("chat", {}).get("id")
        sender      = message_obj.get("from", {}).get("first_name", "Cristian")

        if not text or not chat_id:
            return {"statusCode": 200, "body": "ok"}

        logger.info("msg from %s: %s", sender, text)

        result = parse_message(text, sender_name=sender)

        if result.error:
            reply(update, result.error)
            return {"statusCode": 200, "body": "ok"}

        if result.tipo == "resumen":
            sh      = get_sheet()
            data    = get_monthly_summary(sh)
            summary = _format_summary(data, result.scope_hint)
            reply(update, summary)
            return {"statusCode": 200, "body": "ok"}

        response_text = _handle_registro(result, update)
        reply(update, response_text)

    except Exception as exc:
        logger.exception("Error en finance-handler: %s", exc)
        try:
            body    = json.loads(event.get("body") or "{}")
            chat_id = body.get("message", {}).get("chat", {}).get("id")
            if chat_id:
                send_message(chat_id, f"❌ Error interno: {exc}")
        except Exception:
            pass

    return {"statusCode": 200, "body": "ok"}

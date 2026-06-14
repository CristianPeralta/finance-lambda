"""
sheets.py — Google Sheets client for Lambda.
Key difference from the RPi version: credentials are loaded from a JSON env var,
not from a file path.
"""

import base64
import json
import os
from datetime import date, datetime
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_sheet():
    raw    = os.environ["FINANCE_SA_KEY_JSON"]
    sa_key = json.loads(base64.b64decode(raw).decode("utf-8"))
    creds  = Credentials.from_service_account_info(sa_key, scopes=SCOPES)
    gc     = gspread.authorize(creds)
    return gc.open_by_key(os.environ["FINANCE_SHEET_ID"])


def append_row(sh, tab: str, row: list) -> None:
    ws = sh.worksheet(tab)
    ws.append_row(row, value_input_option="USER_ENTERED")


def _parse_amount(val) -> float:
    try:
        return float(str(val).replace(",", ".").strip())
    except (ValueError, TypeError):
        return 0.0


def _parse_date(val) -> Optional[date]:
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(val).strip(), fmt).date()
        except ValueError:
            continue
    return None


def _is_current_month(record: dict, date_key: str = "Fecha") -> bool:
    today = date.today()
    d = _parse_date(record.get(date_key, ""))
    return bool(d and d.year == today.year and d.month == today.month)


def get_monthly_summary(sh) -> dict:
    """Return current-month totals for MANTYS and Pareja. Used by handler (resumen command) and alert."""
    today = date.today()

    def tab_total(tab_name: str, tipo: str, amount_key: str = "Monto", estado_key: str = None, estado_val: str = None) -> float:
        ws      = sh.worksheet(tab_name)
        records = ws.get_all_records()
        total   = 0.0
        for r in records:
            if not _is_current_month(r):
                continue
            if str(r.get("Tipo", "")).lower() != tipo:
                continue
            if estado_key and str(r.get(estado_key, "")).lower() != estado_val:
                continue
            total += _parse_amount(r.get(amount_key, 0))
        return total

    mantys_gastos   = tab_total("MANTYS", "gasto")
    mantys_ingresos = tab_total("MANTYS", "ingreso", estado_key="Estado", estado_val="cobrado")
    pareja_gastos   = tab_total("Pareja", "gasto")
    pareja_ingresos = tab_total("Pareja", "ingreso")

    return {
        "month":           today.strftime("%B %Y"),
        "mantys_gastos":   mantys_gastos,
        "mantys_ingresos": mantys_ingresos,
        "mantys_ganancia": mantys_ingresos - mantys_gastos,
        "pareja_gastos":   pareja_gastos,
        "pareja_ingresos": pareja_ingresos,
        "pareja_balance":  pareja_ingresos - pareja_gastos,
    }


def get_monthly_totals_by_scope(sh, scope: str) -> dict:
    """Return current-month spending for a given scope. Used by alert to compare against budget."""
    tab     = "MANTYS" if scope == "mantys" else "Pareja"
    ws      = sh.worksheet(tab)
    records = ws.get_all_records()

    gastos = sum(
        _parse_amount(r.get("Monto", 0))
        for r in records
        if _is_current_month(r) and str(r.get("Tipo", "")).lower() == "gasto"
    )

    return {"gastos": gastos, "month": date.today().strftime("%B %Y")}

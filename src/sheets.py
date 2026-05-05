"""
sheets.py — Google Sheets client para Lambda.
Diferencia clave vs RPi: carga credenciales desde env var JSON (no desde archivo).
"""

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
    sa_key = json.loads(os.environ["FINANCE_SA_KEY_JSON"])
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
    """
    Retorna un dict con totales del mes actual para MANTYS y Pareja.
    Usado por handler.py (comando 'resumen') y alert.py.
    """
    today = date.today()

    def tab_total(tab_name: str, amount_key: str = "Monto", estado_key: str = None, estado_val: str = None) -> float:
        ws      = sh.worksheet(tab_name)
        records = ws.get_all_records()
        total   = 0.0
        for r in records:
            if not _is_current_month(r):
                continue
            if estado_key and str(r.get(estado_key, "")).lower() != estado_val:
                continue
            total += _parse_amount(r.get(amount_key, 0))
        return total

    mantys_gastos   = tab_total("MANTYS_Gastos")
    mantys_ingresos = tab_total("MANTYS_Ingresos", estado_key="Estado", estado_val="cobrado")
    pareja_gastos   = tab_total("Pareja_Gastos")
    pareja_ingresos = tab_total("Pareja_Ingresos")

    return {
        "month":            today.strftime("%B %Y"),
        "mantys_gastos":    mantys_gastos,
        "mantys_ingresos":  mantys_ingresos,
        "mantys_ganancia":  mantys_ingresos - mantys_gastos,
        "pareja_gastos":    pareja_gastos,
        "pareja_ingresos":  pareja_ingresos,
        "pareja_balance":   pareja_ingresos - pareja_gastos,
    }


def get_monthly_totals_by_scope(sh, scope: str) -> dict:
    """
    Retorna totales del mes para un scope específico ('mantys' o 'pareja').
    Usado por alert.py para comparar contra presupuesto.
    """
    today = date.today()

    if scope == "mantys":
        gastos_tab   = "MANTYS_Gastos"
        ingresos_tab = "MANTYS_Ingresos"
    else:
        gastos_tab   = "Pareja_Gastos"
        ingresos_tab = "Pareja_Ingresos"

    ws_g    = sh.worksheet(gastos_tab)
    records = ws_g.get_all_records()

    gastos = sum(
        _parse_amount(r.get("Monto", 0))
        for r in records
        if _is_current_month(r)
    )

    return {"gastos": gastos, "month": today.strftime("%B %Y")}

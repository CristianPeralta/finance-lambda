#!/usr/bin/env python3
"""
update_resumen.py — Rebuilds the Resumen sheet with current-month totals.

Reads data from MANTYS, Pareja, and personal user tabs and writes a
structured summary. Run manually or call update_resumen_sheet(sh) from Lambda.

Usage:
  python src/update_resumen.py
"""

import os
import sys
from datetime import date

_USER1 = os.environ.get("FINANCE_USER1", "user1").lower()
_USER2 = os.environ.get("FINANCE_USER2", "user2").lower()

sys.path.insert(0, os.path.dirname(__file__))


# ── Credential loader (for local runs) ───────────────────────────────────────

def _load_samconfig():
    import tomllib
    path = os.path.join(os.path.dirname(__file__), "..", "samconfig.toml")
    with open(path, "rb") as f:
        config = tomllib.load(f)
    for item in config["default"]["deploy"]["parameters"]["parameter_overrides"]:
        key, _, val = item.partition("=")
        if key == "FinanceSheetId":
            os.environ.setdefault("FINANCE_SHEET_ID", val)
        elif key == "FinanceSaKeyJson":
            os.environ.setdefault("FINANCE_SA_KEY_JSON", val)


# ── Data helpers ──────────────────────────────────────────────────────────────

def _parse_amount(val) -> float:
    try:
        return float(str(val).replace(",", ".").strip())
    except (ValueError, TypeError):
        return 0.0


def _parse_fecha(fecha_str: str):
    """Return (month, year) tuple from DD/MM/YYYY string, or None."""
    try:
        parts = str(fecha_str).strip().split("/")
        return (int(parts[1]), int(parts[2]))
    except (IndexError, ValueError):
        return None


def _detect_active_month(all_records: list[list]) -> tuple:
    """
    Return the (month, year) to display: current month if it has data,
    otherwise the most recent month that does.
    """
    today = date.today()
    current = (today.month, today.year)

    months_with_data = set()
    for records in all_records:
        for r in records:
            my = _parse_fecha(r.get("Fecha", ""))
            if my:
                months_with_data.add(my)

    if current in months_with_data:
        return current
    if months_with_data:
        return max(months_with_data)
    return current


def _in_month(fecha_str: str, month: int, year: int) -> bool:
    my = _parse_fecha(fecha_str)
    return my == (month, year)


def _read_tab(sh, tab_name: str) -> list[dict]:
    ws = sh.worksheet(tab_name)
    return ws.get_all_records()


def _sum(records, tipo, mes, categoria=None, estado=None, col_monto="Monto") -> float:
    total = 0.0
    for r in records:
        if not _in_month(r.get("Fecha", ""), *mes):
            continue
        if str(r.get("Tipo", "")).lower() != tipo:
            continue
        if categoria and str(r.get("Categoria", "")).lower() != categoria:
            continue
        if estado and str(r.get("Estado", "")).lower() != estado:
            continue
        total += _parse_amount(r.get(col_monto, 0))
    return total


def _sum_by_cat(records, tipo, mes, categories: list) -> dict:
    return {cat: _sum(records, tipo, mes, categoria=cat) for cat in categories}


# ── Section builders ──────────────────────────────────────────────────────────

MANTYS_CATS   = ["filamento", "insumos", "herramientas", "marketing", "envio", "otro-mantys"]
PAREJA_CATS   = ["comida", "servicios", "salud", "ocio", "ropa", "transporte", "ahorro", "otro-pareja"]
PERSONAL_CATS = ["suscripciones", "educacion", "tecnologia", "salud", "ocio", "ropa", "transporte", "otros"]


def _fmt(amount: float) -> str:
    return f"S/ {amount:.2f}"


def build_rows(sh) -> list:
    today    = date.today()

    mantys = _read_tab(sh, "MANTYS")
    pareja = _read_tab(sh, "Pareja")
    user1  = _read_tab(sh, _USER1.capitalize())
    user2  = _read_tab(sh, _USER2.capitalize())

    # Use current month if it has data, otherwise fall back to most recent month
    mes = _detect_active_month([mantys, pareja, user1, user2])
    MESES_ES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    mes_label = f"{MESES_ES[mes[0]]} {mes[1]}"
    suffix    = " (mes actual)" if mes == (today.month, today.year) else " (último mes con datos)"

    rows = []

    # ── Header ────────────────────────────────────────────────────────────────
    rows += [
        [f"Resumen Financiero — {mes_label}{suffix}", f"Actualizado: {today.strftime('%d/%m/%Y')}"],
        ["", ""],
    ]

    # ── MANTYS ────────────────────────────────────────────────────────────────
    m_ing_cobrado   = _sum(mantys, "ingreso", mes, estado="cobrado")
    m_ing_pendiente = _sum(mantys, "ingreso", mes, estado="pendiente")
    m_gastos        = _sum(mantys, "gasto",   mes)
    m_ganancia      = m_ing_cobrado - m_gastos
    m_cats          = _sum_by_cat(mantys, "gasto", mes, MANTYS_CATS)

    rows += [
        ["── MANTYS ──", ""],
        ["Ingresos cobrados", _fmt(m_ing_cobrado)],
        ["Ingresos pendientes", _fmt(m_ing_pendiente)],
        ["Gastos", _fmt(m_gastos)],
        ["Ganancia neta", _fmt(m_ganancia)],
        ["", ""],
        ["  Gastos por categoría", ""],
    ]
    for cat, total in m_cats.items():
        rows.append([f"  {cat}", _fmt(total)])
    rows.append(["", ""])

    # ── PAREJA ────────────────────────────────────────────────────────────────
    p_ing     = _sum(pareja, "ingreso", mes)
    p_gastos  = _sum(pareja, "gasto",   mes)
    p_cats    = _sum_by_cat(pareja, "gasto", mes, PAREJA_CATS)

    rows += [
        ["── PAREJA ──", ""],
        ["Ingresos", _fmt(p_ing)],
        ["Gastos", _fmt(p_gastos)],
        ["Balance", _fmt(p_ing - p_gastos)],
        ["", ""],
        ["  Gastos por categoría", ""],
    ]
    for cat, total in p_cats.items():
        rows.append([f"  {cat}", _fmt(total)])
    rows.append(["", ""])

    # ── USER1 ─────────────────────────────────────────────────────────────────
    u1_ing    = _sum(user1, "ingreso", mes)
    u1_gastos = _sum(user1, "gasto",   mes)
    u1_cats   = _sum_by_cat(user1, "gasto", mes, PERSONAL_CATS)

    rows += [
        [f"── {_USER1.upper()} ──", ""],
        ["Ingresos", _fmt(u1_ing)],
        ["Gastos", _fmt(u1_gastos)],
        ["Balance", _fmt(u1_ing - u1_gastos)],
        ["", ""],
        ["  Gastos por categoría", ""],
    ]
    for cat, total in u1_cats.items():
        rows.append([f"  {cat}", _fmt(total)])
    rows.append(["", ""])

    # ── USER2 ─────────────────────────────────────────────────────────────────
    u2_ing    = _sum(user2, "ingreso", mes)
    u2_gastos = _sum(user2, "gasto",   mes)
    u2_cats   = _sum_by_cat(user2, "gasto", mes, PERSONAL_CATS)

    rows += [
        [f"── {_USER2.upper()} ──", ""],
        ["Ingresos", _fmt(u2_ing)],
        ["Gastos", _fmt(u2_gastos)],
        ["Balance", _fmt(u2_ing - u2_gastos)],
        ["", ""],
        ["  Gastos por categoría", ""],
    ]
    for cat, total in u2_cats.items():
        rows.append([f"  {cat}", _fmt(total)])

    return rows


# ── Public API (called from Lambda weekly.py) ─────────────────────────────────

def update_resumen_sheet(sh) -> None:
    ws   = sh.worksheet("Resumen")
    rows = build_rows(sh)
    ws.clear()
    ws.append_rows(rows, value_input_option="USER_ENTERED")


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    _load_samconfig()
    from sheets import get_sheet
    sh = get_sheet()
    update_resumen_sheet(sh)
    print("✅ Resumen actualizado.")

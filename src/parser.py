"""
parser.py — Telegram message parsing logic.

Supported commands:
  /gasto  [pareja|mantys|personal] [amount] [concept]
  /ingreso [pareja|mantys|personal] [amount] [concept]
  resumen
  resumen mantys
"""

import re
from dataclasses import dataclass
from typing import Optional


# ─── Categories ───────────────────────────────────────────────────────────────

MANTYS_CATS = {
    "filamento":    ["filamento", "pla", "petg", "resina", "rollo"],
    "insumos":      ["insumo", "pegamento", "lija", "laca", "barniz", "guante", "papel"],
    "herramientas": ["herramienta", "alicate", "pinza", "bisturi", "balanza", "pincel"],
    "marketing":    ["marketing", "publicidad", "foto", "video", "diseño", "sticker", "tarjeta"],
    "envio":        ["envio", "envío", "delivery", "despacho", "courier", "moto", "pasaje", "entrega"],
    "otro-mantys":  [],
}

PAREJA_CATS = {
    "comida":     ["comida", "mercado", "supermercado", "almuerzo", "cena", "desayuno", "restaurante",
                   "pollo", "arroz", "verdura", "viveres", "víveres", "chicharron", "chicharrón",
                   "anticucho", "ceviche", "menu", "menú", "lonche", "snack", "fruta", "pan",
                   "carne", "pescado", "leche", "huevo", "fideos", "papa", "tomate", "embutido",
                   "bebida", "refresco", "jugo", "cafe", "café", "panaderia", "pollería", "polleria",
                   "queso", "sandia", "sandía", "azucar", "azúcar", "mantequilla", "aceite",
                   "atun", "atún", "galleta", "chocolate", "yogur", "helado", "sopa"],
    "servicios":  ["luz", "agua", "internet", "alquiler", "renta", "gas", "telefono", "celular"],
    "salud":      ["medico", "farmacia", "medicina", "clinica", "doctor", "dentista", "salud"],
    "ocio":       ["cine", "peliculas", "netflix", "spotify", "juego", "paseo", "salida", "ocio"],
    "ropa":       ["ropa", "zapato", "zapatilla"],
    "transporte": ["taxi", "bus", "gasolina", "uber", "indriver", "transporte"],
    "ahorro":     ["ahorro", "ahorrar", "guardar"],
    "otro-pareja": [],
}

PERSONAL_CATS = {
    "suscripciones": ["spotify", "netflix", "youtube", "amazon", "suscripcion", "plan"],
    "educacion":     ["curso", "udemy", "libro", "educacion", "capacitacion", "clase"],
    "tecnologia":    ["laptop", "celular", "teclado", "mouse", "monitor", "disco", "cable", "cargador"],
    "salud":         ["medico", "farmacia", "medicina", "clinica", "doctor", "dentista", "gym"],
    "ocio":          ["cine", "juego", "paseo", "salida", "ocio", "viaje"],
    "ropa":          ["ropa", "zapato", "zapatilla", "polo", "pantalon"],
    "transporte":    ["taxi", "bus", "gasolina", "uber", "indriver", "pasaje"],
    "otros-personal": [],
}

CLIENTES_CONOCIDOS = {
    "victor": "#001",
    "alvaro": "#002",
}

VALID_SCOPES = ["pareja", "mantys", "cristian", "roxsy"]

HELP_TEXT = (
    "Comandos disponibles:\n\n"
    "*Gastos:*\n"
    "/gasto pareja 85 comida mercado\n"
    "/gasto mantys 50 filamento\n"
    "/gasto cristian 30 spotify\n"
    "/gasto roxsy 25 farmacia\n\n"
    "*Ingresos:*\n"
    "/ingreso mantys 120 pedido Victor\n"
    "/ingreso pareja 500 sueldo\n"
    "/ingreso cristian 200 freelance\n\n"
    "*Resumen:*\n"
    "/resumen\n"
    "/resumen mantys"
)


# ─── Result dataclass ─────────────────────────────────────────────────────────

@dataclass
class ParseResult:
    tipo: str              # "gasto" | "ingreso" | "resumen"
    scope: Optional[str]   # "mantys" | "pareja" | "personal" | None
    amount: Optional[float]
    category: Optional[str]
    description: str
    paid_by: str
    pedido_num: str
    cliente: str
    scope_hint: Optional[str]  # for resumen: None = both, "mantys" = mantys only
    raw: str
    error: Optional[str]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _detect_category(text: str, scope: str) -> str:
    if scope == "mantys":
        cat_map, default = MANTYS_CATS, "otro-mantys"
    elif scope in ("cristian", "roxsy"):
        cat_map, default = PERSONAL_CATS, "otros"
    else:
        cat_map, default = PAREJA_CATS, "otro-pareja"
    t = text.lower()
    for cat, keywords in cat_map.items():
        for kw in keywords:
            if re.search(r"(?<!\w)" + re.escape(kw) + r"(?!\w)", t):
                return cat
    return default


def _detect_known_client(text: str):
    t = text.lower()
    for nombre, pedido_num in CLIENTES_CONOCIDOS.items():
        if nombre in t:
            return nombre.capitalize(), pedido_num
    return None, None


def _detect_paid_by(text: str, default: str = "Cristian") -> str:
    return "Roxsy" if ("roxsy" in text.lower() or "ella" in text.lower()) else default


def _err(msg: str, raw: str) -> ParseResult:
    return ParseResult(
        tipo="", scope=None, amount=None, category=None,
        description="", paid_by="", pedido_num="", cliente="",
        scope_hint=None, raw=raw, error=msg,
    )


# ─── Public API ───────────────────────────────────────────────────────────────

def parse_message(raw_message: str, sender_name: str = "Cristian") -> ParseResult:
    """Parse a Telegram message and return a ParseResult."""
    text = raw_message.strip()
    lower = text.lower()

    # ── resumen ───────────────────────────────────────────────────────────────
    if lower.startswith("resumen") or lower.startswith("/resumen"):
        scope_hint = "mantys" if "mantys" in lower else None
        return ParseResult(
            tipo="resumen", scope=None, amount=None, category=None,
            description="", paid_by="", pedido_num="", cliente="",
            scope_hint=scope_hint, raw=raw_message, error=None,
        )

    # ── /gasto or /ingreso ────────────────────────────────────────────────────
    match = re.match(r"^/(gasto|ingreso)\s+(.+)$", text, re.IGNORECASE)
    if not match:
        return _err(f"No entendí el comando.\n\n{HELP_TEXT}", raw_message)

    tipo  = match.group(1).lower()
    rest  = match.group(2).strip()
    words = rest.split()

    # scope
    if not words or words[0].lower() not in VALID_SCOPES:
        return _err(
            f"Especifica el alcance: pareja, mantys o personal.\n\n"
            f"Ejemplo: /gasto pareja 85 comida",
            raw_message,
        )
    scope = words[0].lower()
    words = words[1:]

    # amount — first token that looks like a number
    amount = None
    amount_idx = None
    for i, w in enumerate(words):
        try:
            amount = float(w.replace(",", "."))
            amount_idx = i
            break
        except ValueError:
            continue

    if amount is None:
        return _err(
            f"No encontré el monto.\n\nEjemplo: /gasto {scope} 85 comida",
            raw_message,
        )

    concept_words = words[:amount_idx] + words[amount_idx + 1:]
    description   = " ".join(concept_words).strip() or scope
    paid_by       = _detect_paid_by(description, default=sender_name)
    category      = _detect_category(description, scope)

    # Extra fields for MANTYS income
    pedido_num = ""
    cliente    = ""
    if tipo == "ingreso" and scope == "mantys":
        cliente, pedido_num = _detect_known_client(description)
        cliente    = cliente or ""
        pedido_num = pedido_num or ""
        if not pedido_num:
            m = re.search(r"#(\d+)", description)
            pedido_num = f"#{m.group(1)}" if m else ""
        if not cliente:
            m = re.search(r"pedido\s+([A-Za-záéíóúñ]+)", description, re.IGNORECASE)
            cliente = m.group(1).capitalize() if m else ""
        if cliente:
            description = f"Cobro pedido {cliente}".strip()

    return ParseResult(
        tipo=tipo,
        scope=scope,
        amount=amount,
        category=category,
        description=description,
        paid_by=paid_by,
        pedido_num=pedido_num,
        cliente=cliente,
        scope_hint=None,
        raw=raw_message,
        error=None,
    )

"""
parser.py — Telegram message parsing logic.
Ported from finance-bot-skill.py (RPi) to run on Lambda.
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
    "envio":        ["envio", "envío", "delivery", "despacho", "courier", "moto", "pasaje", "pasajes", "entrega", "llevar"],
    "otro-mantys":  [],
}

PAREJA_CATS = {
    "comida":     ["comida", "mercado", "supermercado", "almuerzo", "cena", "desayuno", "restaurante",
                   "pollo", "arroz", "verdura", "viveres", "víveres", "chicharron", "chicharrón",
                   "anticucho", "ceviche", "menu", "menú", "lonche", "snack", "fruta", "pan",
                   "carne", "pescado", "leche", "huevo", "fideos", "papa", "tomate", "embutido",
                   "bebida", "refresco", "jugo", "cafe", "café", "panaderia", "pollería", "polleria"],
    "servicios":  ["luz", "agua", "internet", "alquiler", "renta", "gas", "telefono", "celular"],
    "salud":      ["medico", "farmacia", "medicina", "clinica", "doctor", "dentista", "salud"],
    "ocio":       ["cine", "peliculas", "netflix", "spotify", "juego", "paseo", "salida", "ocio"],
    "ropa":       ["ropa", "zapato", "zapatilla"],
    "transporte": ["taxi", "bus", "gasolina", "uber", "indriver", "transporte"],
    "ahorro":     ["ahorro", "ahorrar", "guardar"],
    "otro-pareja": [],
}

PERSONAL_CATS = {
    "suscripciones": [],
    "educacion":     [],
    "tecnologia":    [],
    "salud":         [],
    "ocio":          [],
    "ropa":          [],
    "transporte":    [],
    "otros-personal": [],
}

ALL_CATS = list(MANTYS_CATS.keys()) + list(PAREJA_CATS.keys()) + list(PERSONAL_CATS.keys())

# ─── Keywords ─────────────────────────────────────────────────────────────────

MANTYS_KEYWORDS  = ["mantys", "negocio", "impresora", "impresion", "3d", "pedido"]
INGRESO_KEYWORDS = ["ingreso", "cobr", "pago recibido", "vendimos", "ganamos", "cobrado"]
PAREJA_KEYWORDS  = [
    "alquiler", "renta", "luz", "agua", "internet", "gas", "mercado",
    "comida", "almuerzo", "cena", "desayuno", "supermercado", "farmacia",
    "medico", "doctor", "clinica", "cine", "paseo", "ropa", "zapato",
    "taxi", "bus", "uber", "indriver", "ahorro", "servicios",
]

CLIENTES_CONOCIDOS = {
    "victor": "#001",
    "alvaro": "#002",
}


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
    error: Optional[str]       # set when parsing fails; handler sends this to the user


# ─── Detection helpers ────────────────────────────────────────────────────────

def _clean_message(text: str) -> str:
    return re.sub(r"^/\w+\s*", "", text).strip()


def _detect_amount(text: str) -> Optional[float]:
    match = re.search(r"\b(\d+(?:[.,]\d+)?)\b", text)
    if match:
        return float(match.group(1).replace(",", "."))
    return None


def _detect_type(text: str) -> str:
    t = text.lower()
    for kw in INGRESO_KEYWORDS:
        if kw in t:
            return "ingreso"
    return "gasto"


def _detect_scope(text: str) -> Optional[str]:
    t = text.lower()
    has_mantys = any(kw in t for kw in MANTYS_KEYWORDS)
    has_pareja = any(kw in t for kw in PAREJA_KEYWORDS)
    if has_mantys and not has_pareja:
        return "mantys"
    if has_pareja and not has_mantys:
        return "pareja"
    if has_mantys and has_pareja:
        return "mantys"  # MANTYS takes priority when both match
    return None


def _detect_category(text: str, scope: str) -> str:
    if scope == "mantys":
        cat_map, default = MANTYS_CATS, "otro-mantys"
    elif scope == "personal":
        cat_map, default = PERSONAL_CATS, "otros-personal"
    else:
        cat_map, default = PAREJA_CATS, "otro-pareja"
    t = text.lower()
    for cat, keywords in cat_map.items():
        for kw in keywords:
            if kw in t:
                return cat
    return default


def _extract_scope_arg(text: str):
    """
    Detects explicit scope and category at the start of the message.
    "pareja comida 85 mercado" -> ("pareja", "comida", "85 mercado")
    "pareja 280 alquiler"      -> ("pareja", None, "280 alquiler")
    "280 alquiler"             -> (None, None, "280 alquiler")
    """
    words = text.strip().split()
    scope = None
    cat = None
    consumed = 0
    scope_args = ["mantys", "pareja", "personal"]

    if words and words[0].lower() in scope_args:
        scope = words[0].lower()
        consumed = 1
        if len(words) > 1 and words[1].lower() in ALL_CATS:
            cat = words[1].lower()
            consumed = 2

    rest = " ".join(words[consumed:])
    return scope, cat, rest


def _extract_description(text: str) -> str:
    t = re.sub(r"\b\d+(?:[.,]\d+)?\b", "", text)
    triggers = ["gastamos", "gaste", "gasté", "compramos", "compré", "compre",
                "pagamos", "pagué", "pague", "ingreso", "cobré", "cobre",
                "mantys", "pareja", "en", "de", "por", "s/", "soles", "del",
                "pedido", "pago", "cobro"]
    words = t.lower().split()
    filtered = [w for w in words if w not in triggers and len(w) > 1]
    return " ".join(filtered).strip() or text.strip()


def _detect_known_client(text: str):
    t = text.lower()
    for nombre, pedido_num in CLIENTES_CONOCIDOS.items():
        if nombre in t:
            return nombre.capitalize(), pedido_num
    return None, None


def _detect_paid_by(text: str, default: str = "Cristian") -> str:
    t = text.lower()
    if "roxsy" in t or "ella" in t:
        return "Roxsy"
    return default


# ─── Public API ───────────────────────────────────────────────────────────────

def parse_message(raw_message: str, sender_name: str = "Cristian") -> ParseResult:
    """Parse a Telegram message and return a ParseResult. Single entry point for handler.py."""
    # Detect type intent before stripping command prefixes
    forced_tipo = None
    if re.match(r"^/ingreso\b", raw_message, re.IGNORECASE):
        forced_tipo = "ingreso"
    elif re.match(r"^/gasto\b", raw_message, re.IGNORECASE):
        forced_tipo = "gasto"

    message = _clean_message(raw_message)

    if message.lower().startswith("resumen"):
        scope_hint = "mantys" if "mantys" in message.lower() else None
        return ParseResult(
            tipo="resumen",
            scope=None,
            amount=None,
            category=None,
            description="",
            paid_by="",
            pedido_num="",
            cliente="",
            scope_hint=scope_hint,
            raw=raw_message,
            error=None,
        )

    scope_arg, cat_arg, message = _extract_scope_arg(message)

    tipo  = forced_tipo if forced_tipo else _detect_type(message)
    scope = scope_arg if scope_arg else _detect_scope(message)

    # A known client name implies MANTYS
    if scope is None:
        cliente_hint, _ = _detect_known_client(message)
        if cliente_hint:
            scope = "mantys"

    amount  = _detect_amount(message)
    desc    = _extract_description(message)
    paid_by = _detect_paid_by(message, default=sender_name)

    if amount is None:
        return ParseResult(
            tipo=tipo, scope=scope, amount=None, category=None,
            description=desc, paid_by=paid_by, pedido_num="", cliente="",
            scope_hint=None, raw=raw_message,
            error="No encontré un monto. Ejemplo: *gastamos 50 en comida*",
        )

    if scope is None:
        return ParseResult(
            tipo=tipo, scope=None, amount=amount, category=None,
            description=desc, paid_by=paid_by, pedido_num="", cliente="",
            scope_hint=None, raw=raw_message,
            error="¿Es gasto de MANTYS o de la pareja? Especifica: *mantys 50 en filamento* o *pareja 85 en comida*",
        )

    cat = cat_arg if cat_arg else _detect_category(message, scope)

    # Extra fields for MANTYS income entries
    pedido_num = ""
    cliente    = ""
    if tipo == "ingreso" and scope == "mantys":
        cliente, pedido_num = _detect_known_client(message)
        cliente    = cliente or ""
        pedido_num = pedido_num or ""
        if not pedido_num:
            m = re.search(r"#(\d+)", message)
            pedido_num = f"#{m.group(1)}" if m else ""
        if not cliente:
            m = re.search(r"pedido\s+([A-Za-záéíóúñ]+)", message, re.IGNORECASE)
            cliente = m.group(1).capitalize() if m else ""
        desc = f"Cobro pedido {cliente}".strip() if cliente else desc

    return ParseResult(
        tipo=tipo,
        scope=scope,
        amount=amount,
        category=cat,
        description=desc,
        paid_by=paid_by,
        pedido_num=pedido_num,
        cliente=cliente,
        scope_hint=None,
        raw=raw_message,
        error=None,
    )

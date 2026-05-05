# finance-lambda

Sistema de finanzas personal cloud-native. Reemplaza el script Python en RPi por tres Lambdas en AWS, eliminando la dependencia de hardware local.

## Arquitectura

```
Telegram mensaje
    │
    ▼
Telegram Bot API
    │  (webhook POST)
    ▼
API Gateway HTTP API
    │  POST /webhook
    ▼
Lambda: finance-handler
    ├── parser.py     → detecta tipo/scope/monto/categoría
    ├── sheets.py     → escribe en Google Sheets
    └── telegram.py   → responde confirmación al usuario


EventBridge cron (lunes 8am Peru)
    ▼
Lambda: finance-weekly           [Fase 2]
    ├── lee Google Sheets (semana actual)
    └── envía resumen a Telegram


EventBridge cron (diario 8pm Peru)
    ▼
Lambda: finance-alert            [Fase 2]
    ├── lee gastos del mes vs presupuesto
    └── alerta si supera 80% → Telegram


[Vault sync sigue como cron local en PC — no migrado]
finance-sync.py → lee Sheets → genera markdowns en Obsidian
```

## Google Sheets esperados

| Tab                | Columnas                                                           |
|--------------------|--------------------------------------------------------------------|
| `MANTYS_Gastos`    | Fecha, Descripcion, Categoria, Monto, Pagado_por, Mensaje_original |
| `MANTYS_Ingresos`  | Fecha, Pedido_num, Cliente, Descripcion, Monto, Estado, Mensaje_original |
| `Pareja_Gastos`    | Fecha, Descripcion, Categoria, Monto, Pagado_por, Mensaje_original |
| `Pareja_Ingresos`  | Fecha, Descripcion, Fuente, Monto, Mensaje_original               |
| `Personal_Gastos`  | Fecha, Descripcion, Categoria, Monto, Mensaje_original            |

## Comandos que entiende el bot

```
gastamos 50 en filamento MANTYS     → gasto MANTYS, categoría filamento
gaste 85 en comida                  → gasto pareja, categoría comida
pagamos 300 de alquiler             → gasto pareja, categoría servicios
ingreso 120 pedido Victor MANTYS    → ingreso MANTYS
mantys filamento 50                 → gasto MANTYS explícito con categoría
pareja comida 85 mercado            → gasto pareja explícito con categoría
resumen                             → resumen mes actual (MANTYS + pareja)
resumen mantys                      → solo MANTYS
```

## Setup

### 1. Prerrequisitos

- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) configurado (`aws configure`)
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- Python 3.12
- Service account de Google con permisos en el Sheet (rol Editor)
- Bot de Telegram creado con @BotFather

### 2. Obtener el Chat ID de Telegram

```bash
# 1. Manda cualquier mensaje al bot
# 2. Consulta updates:
curl "https://api.telegram.org/bot<TOKEN>/getUpdates"
# Busca: result[0].message.chat.id
```

### 3. Preparar credenciales

```bash
# Minificar el JSON del service account a una sola línea:
cat finance-sa.json | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin)))"
```

### 4. Configurar SAM

```bash
cp samconfig.toml.example samconfig.toml
# Editar samconfig.toml con tus valores reales
```

### 5. Build y deploy

```bash
sam build
sam deploy
# Primera vez: sam deploy --guided
```

### 6. Registrar el webhook en Telegram

El comando `sam deploy` muestra el output `WebhookUrl`. Úsalo para registrar el webhook:

```bash
curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=<WEBHOOK_URL>"
# Verificar:
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

### 7. Probar

Envía al bot: `gastamos 50 en comida`

Debería responder: `✅ Gasto pareja: *comida* — S/ 50.00 (Cristian)`

## Desarrollo local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r src/requirements.txt

# Simular evento Telegram:
export FINANCE_SHEET_ID=...
export FINANCE_SA_KEY_JSON='...'
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHAT_ID=...

echo '{"body":"{\"message\":{\"text\":\"gastamos 50 en comida\",\"chat\":{\"id\":123},\"from\":{\"first_name\":\"Cristian\"}}}"}' | \
  python3 -c "
import sys, json
sys.path.insert(0, 'src')
from handler import lambda_handler
event = json.load(sys.stdin)
print(lambda_handler(event, None))
"
```

## Estructura

```
finance-lambda/
├── src/
│   ├── handler.py          # Lambda webhook Telegram (Fase 1 ✅)
│   ├── weekly.py           # Lambda resumen semanal (Fase 2)
│   ├── alert.py            # Lambda alerta presupuesto (Fase 2)
│   ├── sheets.py           # Google Sheets client
│   ├── parser.py           # Parsing de mensajes
│   ├── telegram.py         # Helper Telegram API
│   └── requirements.txt
├── template.yaml           # AWS SAM — sin valores reales
├── samconfig.toml.example  # Config SAM con placeholders
├── .env.example            # Vars con descripción
├── .gitignore
└── README.md
```

## Free Tier

| Servicio      | Límite free                        | Uso esperado          |
|---------------|------------------------------------|-----------------------|
| Lambda        | 1M requests/mes, 400K GB-s/mes     | ~300 req/mes — free ∞ |
| API Gateway   | 1M requests/mes (12 meses)         | ~300 req/mes          |
| EventBridge   | Always free (scheduled events)     | 2 eventos/día         |

## Roadmap

- [x] Fase 1: handler.py + SAM template + infraestructura
- [ ] Fase 2: alert.py — alertas diarias de presupuesto (80%)
- [ ] Fase 2: weekly.py — resumen semanal los lunes
- [ ] Hacer el repo público una vez verificado que no hay nada sensible

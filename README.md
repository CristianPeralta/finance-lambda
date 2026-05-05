# finance-lambda

Cloud-native personal finance system. Replaces a Python script running on a Raspberry Pi with three AWS Lambda functions, removing the dependency on local hardware.

## Architecture

```
Telegram message
    │
    ▼
Telegram Bot API
    │  (webhook POST)
    ▼
API Gateway HTTP API
    │  POST /webhook
    ▼
Lambda: finance-handler
    ├── parser.py   → detects type / scope / amount / category
    ├── sheets.py   → writes to Google Sheets
    └── telegram.py → sends confirmation back to user


EventBridge cron (Monday 8am Peru)
    ▼
Lambda: finance-weekly           [Phase 2]
    ├── reads Google Sheets (current week)
    └── sends summary to Telegram


EventBridge cron (daily 8pm Peru)
    ▼
Lambda: finance-alert            [Phase 2]
    ├── reads current month spending vs budget
    └── alerts if > 80% → Telegram


[Vault sync stays as a local cron on PC — not migrated]
finance-sync.py → reads Sheets → generates markdown files in Obsidian
```

## Google Sheets structure

| Tab                | Columns                                                              |
|--------------------|----------------------------------------------------------------------|
| `MANTYS_Gastos`    | Fecha, Descripcion, Categoria, Monto, Pagado_por, Mensaje_original  |
| `MANTYS_Ingresos`  | Fecha, Pedido_num, Cliente, Descripcion, Monto, Estado, Mensaje_original |
| `Pareja_Gastos`    | Fecha, Descripcion, Categoria, Monto, Pagado_por, Mensaje_original  |
| `Pareja_Ingresos`  | Fecha, Descripcion, Fuente, Monto, Mensaje_original                 |
| `Personal_Gastos`  | Fecha, Descripcion, Categoria, Monto, Mensaje_original              |

## Supported bot commands

```
gastamos 50 en filamento MANTYS     → MANTYS expense, category: filamento
gaste 85 en comida                  → pareja expense, category: comida
pagamos 300 de alquiler             → pareja expense, category: servicios
ingreso 120 pedido Victor MANTYS    → MANTYS income
mantys filamento 50                 → explicit MANTYS expense with category
pareja comida 85 mercado            → explicit pareja expense with category
resumen                             → current month summary (MANTYS + pareja)
resumen mantys                      → MANTYS only
```

## Setup

### 1. Prerequisites

- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) configured (`aws configure`)
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- Python 3.12
- Google service account with Editor access to the Sheet
- Telegram bot created via @BotFather

### 2. Get your Telegram Chat ID

```bash
# 1. Send any message to your bot
# 2. Fetch updates:
curl "https://api.telegram.org/bot<TOKEN>/getUpdates"
# Look for: result[0].message.chat.id
```

### 3. Minify the service account JSON

```bash
cat finance-sa.json | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin)))"
```

### 4. Configure SAM

```bash
cp samconfig.toml.example samconfig.toml
# Edit samconfig.toml with your real values
```

### 5. Build and deploy

```bash
sam build
sam deploy          # use --guided on first run
```

### 6. Register the Telegram webhook

`sam deploy` prints a `WebhookUrl` output. Register it with Telegram:

```bash
curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=<WEBHOOK_URL>"

# Verify:
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

### 7. Test

Send the bot: `gastamos 50 en comida`

Expected reply: `✅ Gasto pareja: *comida* — S/ 50.00 (Cristian)`

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r src/requirements.txt

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

## Project structure

```
finance-lambda/
├── src/
│   ├── handler.py          # Telegram webhook Lambda (Phase 1 ✅)
│   ├── weekly.py           # Weekly summary Lambda (Phase 2)
│   ├── alert.py            # Budget alert Lambda (Phase 2)
│   ├── sheets.py           # Google Sheets client
│   ├── parser.py           # Message parsing logic
│   ├── telegram.py         # Telegram API helpers
│   └── requirements.txt
├── template.yaml           # AWS SAM — no real values
├── samconfig.toml.example  # SAM config template
├── .env.example            # Env vars with descriptions
├── .gitignore
└── README.md
```

## Free Tier

| Service       | Free limit                         | Expected usage        |
|---------------|------------------------------------|-----------------------|
| Lambda        | 1M requests/mo, 400K GB-s/mo       | ~300 req/mo — free ∞  |
| API Gateway   | 1M requests/mo (12 months)         | ~300 req/mo           |
| EventBridge   | Always free (scheduled events)     | 2 events/day          |

## Roadmap

- [x] Phase 1: handler.py + SAM template + infrastructure
- [ ] Phase 2: alert.py — daily budget alerts (80% threshold)
- [ ] Phase 2: weekly.py — automatic Monday summary

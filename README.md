# finance-lambda

Cloud-native personal finance system. A Telegram bot records expenses and income into Google Sheets via AWS Lambda.

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
Lambda: finance-weekly
    ├── reads Google Sheets (current month)
    ├── updates Resumen tab
    └── sends weekly summary to Telegram


EventBridge cron (daily 8pm Peru)
    ▼
Lambda: finance-alert            [Phase 2 — pending]
    ├── reads current month spending vs budget
    └── alerts if > 80% → Telegram
```

## Google Sheets structure

| Tab       | Columns                                                                                        |
|-----------|------------------------------------------------------------------------------------------------|
| `MANTYS`  | Fecha, Tipo, Descripcion, Categoria, Pedido_num, Cliente, Monto, Estado, Pagado_por, Mensaje_original |
| `Pareja`  | Fecha, Tipo, Descripcion, Categoria, Monto, Pagado_por, Fuente, Mensaje_original              |
| `User1`   | Fecha, Tipo, Descripcion, Categoria, Monto, Mensaje_original                                  |
| `User2`   | Fecha, Tipo, Descripcion, Categoria, Monto, Mensaje_original                                  |
| `Resumen` | Auto-generated summary — rebuilt every Monday by finance-weekly                               |

Tab names for `User1` and `User2` are the capitalized values of `FINANCE_USER1` / `FINANCE_USER2`.

## Bot commands

```
/gasto pareja 85 comida           → pareja expense, category: comida
/gasto mantys 50 filamento        → MANTYS expense, category: filamento
/gasto user1 30 spotify           → personal expense for user1
/gasto user2 25 farmacia          → personal expense for user2

/ingreso mantys 500 pedido #12    → MANTYS income, pedido #12
/ingreso pareja 3000 sueldo       → pareja income
/ingreso user1 200 freelance      → personal income for user1

/resumen                          → current month summary (all scopes)
/resumen mantys                   → MANTYS only
```

## Setup

### 1. Prerequisites

- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) configured (`aws configure`)
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- Python 3.12
- Google service account with Editor access to the Sheet
- Telegram bot created via @BotFather

### 2. Create the Google Sheet

Create a spreadsheet with these tabs: `MANTYS`, `Pareja`, `<User1>`, `<User2>`, `Resumen`.

Add the corresponding headers to each tab (see **Google Sheets structure** above).

### 3. Get your Telegram Chat ID

```bash
# 1. Send any message to your bot
# 2. Fetch updates:
curl "https://api.telegram.org/bot<TOKEN>/getUpdates"
# Look for: result[0].message.chat.id
```

### 4. Minify the service account JSON

```bash
cat finance-sa.json | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin)))"
```

### 5. Configure SAM

```bash
cp samconfig.toml.example samconfig.toml
# Edit samconfig.toml — fill in all parameter_overrides with your real values
```

Key parameters:

| Parameter       | Description                                      |
|-----------------|--------------------------------------------------|
| `FinanceSheetId`  | Google Sheet ID (from the URL)                 |
| `FinanceSaKeyJson`| Service account JSON, minified to one line     |
| `TelegramBotToken`| Bot token from @BotFather                      |
| `TelegramChatId`  | Chat ID where the bot sends notifications      |
| `FinanceUser1`    | First personal user (lowercase, e.g. `alice`)  |
| `FinanceUser2`    | Second personal user (lowercase, e.g. `bob`)   |
| `BudgetPareja`    | Monthly budget in soles — default 3000         |
| `BudgetMantys`    | Monthly budget in soles — default 500          |

### 6. Build and deploy

```bash
sam build
sam deploy          # use --guided on first run
```

### 7. Register the Telegram webhook

`sam deploy` prints a `WebhookUrl` output. Register it:

```bash
curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=<WEBHOOK_URL>"

# Verify:
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

### 8. Test

Send the bot: `/gasto pareja 50 comida`

Expected reply: `✅ Gasto pareja: *comida* — S/ 50.00`

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r src/requirements.txt

export FINANCE_SHEET_ID=...
export FINANCE_SA_KEY_JSON='...'
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHAT_ID=...
export FINANCE_USER1=alice
export FINANCE_USER2=bob

python3 -m pytest tests/
```

To invoke the handler locally:

```bash
echo '{"body":"{\"message\":{\"text\":\"/gasto pareja 50 comida\",\"chat\":{\"id\":123},\"from\":{\"first_name\":\"Alice\"}}}"}' | \
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
│   ├── handler.py          # Telegram webhook Lambda
│   ├── weekly.py           # Weekly summary Lambda
│   ├── alert.py            # Budget alert Lambda (Phase 2 — pending)
│   ├── sheets.py           # Google Sheets client
│   ├── parser.py           # Message parsing logic
│   ├── telegram.py         # Telegram API helpers
│   ├── update_resumen.py   # Rebuilds the Resumen tab
│   ├── migrate.py          # One-time migration script (old schema → new)
│   └── requirements.txt
├── template.yaml           # AWS SAM — no real values
├── samconfig.toml.example  # SAM config template
├── .env.example            # Env vars reference for local dev
├── .gitignore
└── README.md
```

## Free Tier

| Service     | Free limit                         | Expected usage       |
|-------------|------------------------------------|-----------------------|
| Lambda      | 1M requests/mo, 400K GB-s/mo       | ~300 req/mo — free ∞ |
| API Gateway | 1M requests/mo (12 months)         | ~300 req/mo           |
| EventBridge | Always free (scheduled events)     | 2 events/day          |

## Roadmap

- [x] Phase 1: Telegram webhook handler + Google Sheets integration
- [x] Phase 2: Weekly summary (Monday 8am Peru)
- [ ] Phase 2: Daily budget alerts (80% threshold)

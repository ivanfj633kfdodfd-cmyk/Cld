# Claude Subscription Bot

Telegram-бот для продажи подписки на Claude AI с оплатой криптовалютой.  
Деплой: **GitHub → Vercel** (serverless, webhook).

---

## Структура

```
ClaudeBot/
├── bot.py                  # Vercel entry point (handler class)
├── config.py               # Все настройки из env
├── keyboards.py            # Все inline-клавиатуры
├── handlers/
│   ├── start.py            # /start, главное меню
│   ├── subscription.py     # Тарифы → валюта → реквизиты → уведомление
│   └── support.py          # Тикет-система + /reply для админа
├── webapp/
│   └── index.html          # Telegram Web App (чат-интерфейс)
├── vercel.json
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Деплой

### 1. GitHub

```bash
git init
git add .
git commit -m "init"
git remote add origin https://github.com/YOUR/claudebot.git
git push -u origin main
```

### 2. Vercel

1. Импортируй репо на [vercel.com](https://vercel.com)
2. В **Settings → Environment Variables** добавь все переменные из `.env.example`
3. После деплоя открой:

```
https://your-project.vercel.app/setup_webhook
```

Это зарегистрирует webhook у Telegram автоматически.

---

## Переменные окружения (Vercel → Settings → Env Vars)

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен бота из @BotFather |
| `ADMIN_ID` | Твой Telegram user ID |
| `WEBHOOK_HOST` | `https://your-project.vercel.app` |
| `WEBHOOK_PATH` | `/webhook` |
| `BANNER_FILE_ID` | URL или file_id баннера (изображение для /start) |
| `WALLET_USDT_TRC20` | Адрес USDT TRC-20 |
| `WALLET_USDT_ERC20` | Адрес USDT ERC-20 |
| `WALLET_TRON` | Адрес TRX |
| `WALLET_BTC` | Адрес Bitcoin |
| `WALLET_ETH` | Адрес Ethereum |
| `WALLET_USDC_ERC20` | Адрес USDC ERC-20 |
| `WALLET_BNB` | Адрес BNB BSC |
| `WALLET_SOL` | Адрес Solana |
| `WALLET_TON` | Адрес TON |

---

## Команды админа

| Команда | Действие |
|---|---|
| `/reply <user_id> <текст>` | Ответить пользователю на его тикет |

---

## Локальный запуск

```bash
pip install -r requirements.txt
cp .env.example .env   # заполни .env
python bot.py          # запустится aiohttp-сервер на :8000
```

Для локального вебхука используй [ngrok](https://ngrok.com):
```bash
ngrok http 8000
# Вставь ngrok-URL в WEBHOOK_HOST в .env
```

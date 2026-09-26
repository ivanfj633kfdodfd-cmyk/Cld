import os
from dotenv import load_dotenv

load_dotenv()

# ── Bot ────────────────────────────────────────────────────────────────────────
BOT_TOKEN: str = os.environ["BOT_TOKEN"]
ADMIN_ID: int = int(os.environ["ADMIN_ID"])

# ── Webhook (не нужны если регистрируешь вручную через Telegram API) ───────────
WEBHOOK_HOST: str = os.getenv("WEBHOOK_HOST", "")
WEBHOOK_PATH: str = os.getenv("WEBHOOK_PATH", "/webhook")
WEBHOOK_URL: str = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# ── Crypto wallets ─────────────────────────────────────────────────────────────
_PLACEHOLDER = "⏳ Адрес ещё не добавлен"

WALLETS: dict[str, dict] = {
    "USDT (TRC-20)": {
        "address": os.getenv("WALLET_USDT_TRC20", _PLACEHOLDER),
        "network": "TRON (TRC-20)",
        "emoji": "💚",
    },
    "USDT (ERC-20)": {
        "address": os.getenv("WALLET_USDT_ERC20", _PLACEHOLDER),
        "network": "Ethereum (ERC-20)",
        "emoji": "💚",
    },
    "TRON (TRX)": {
        "address": os.getenv("WALLET_TRON", _PLACEHOLDER),
        "network": "TRON",
        "emoji": "🔴",
    },
    "Bitcoin (BTC)": {
        "address": os.getenv("WALLET_BTC", _PLACEHOLDER),
        "network": "Bitcoin",
        "emoji": "🟠",
    },
    "Ethereum (ETH)": {
        "address": os.getenv("WALLET_ETH", _PLACEHOLDER),
        "network": "Ethereum",
        "emoji": "🔷",
    },
    "USDC (ERC-20)": {
        "address": os.getenv("WALLET_USDC_ERC20", _PLACEHOLDER),
        "network": "Ethereum (ERC-20)",
        "emoji": "🔵",
    },
    "BNB (BSC)": {
        "address": os.getenv("WALLET_BNB", _PLACEHOLDER),
        "network": "BNB Smart Chain",
        "emoji": "🟡",
    },
    "Solana (SOL)": {
        "address": os.getenv("WALLET_SOL", _PLACEHOLDER),
        "network": "Solana",
        "emoji": "🟣",
    },
    "TON": {
        "address": os.getenv("WALLET_TON", _PLACEHOLDER),
        "network": "TON",
        "emoji": "💎",
    },
}

# ── Plans ──────────────────────────────────────────────────────────────────────
PLANS: dict[str, dict] = {
    "1_month": {
        "label": "1 месяц",
        "price_usd": 20,
        "emoji": "📅",
        "desc": "Полный доступ на 30 дней",
    },
    "3_months": {
        "label": "3 месяца",
        "price_usd": 50,
        "emoji": "📆",
        "desc": "Экономия $10 — самый популярный",
        "badge": "🔥 Хит",
    },
    "6_months": {
        "label": "6 месяцев",
        "price_usd": 90,
        "emoji": "🗓",
        "desc": "Экономия $30 — лучшая цена",
        "badge": "💎 Выгода",
    },
    "1_year": {
        "label": "12 месяцев",
        "price_usd": 160,
        "emoji": "🏆",
        "desc": "Экономия $80 — максимальная выгода",
        "badge": "👑 Pro",
    },
}

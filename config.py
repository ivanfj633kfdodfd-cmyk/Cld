import os
from dotenv import load_dotenv

load_dotenv()

# ── Bot ────────────────────────────────────────────────────────────────────────
BOT_TOKEN: str = os.environ["BOT_TOKEN"]
ADMIN_ID: int = int(os.environ["ADMIN_ID"])

# ── Webhook ────────────────────────────────────────────────────────────────────
WEBHOOK_HOST: str = os.environ["WEBHOOK_HOST"]
WEBHOOK_PATH: str = os.getenv("WEBHOOK_PATH", "/webhook")
WEBHOOK_URL: str = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# ── Crypto wallets ─────────────────────────────────────────────────────────────
WALLETS: dict[str, dict] = {
    "USDT (TRC-20)": {
        "address": os.environ["WALLET_USDT_TRC20"],
        "network": "TRON (TRC-20)",
        "emoji": "💚",
    },
    "USDT (ERC-20)": {
        "address": os.environ["WALLET_USDT_ERC20"],
        "network": "Ethereum (ERC-20)",
        "emoji": "💚",
    },
    "TRON (TRX)": {
        "address": os.environ["WALLET_TRON"],
        "network": "TRON",
        "emoji": "🔴",
    },
    "Bitcoin (BTC)": {
        "address": os.environ["WALLET_BTC"],
        "network": "Bitcoin",
        "emoji": "🟠",
    },
    "Ethereum (ETH)": {
        "address": os.environ["WALLET_ETH"],
        "network": "Ethereum",
        "emoji": "🔷",
    },
    "USDC (ERC-20)": {
        "address": os.environ["WALLET_USDC_ERC20"],
        "network": "Ethereum (ERC-20)",
        "emoji": "🔵",
    },
    "BNB (BSC)": {
        "address": os.environ["WALLET_BNB"],
        "network": "BNB Smart Chain",
        "emoji": "🟡",
    },
    "Solana (SOL)": {
        "address": os.environ["WALLET_SOL"],
        "network": "Solana",
        "emoji": "🟣",
    },
    "TON": {
        "address": os.environ["WALLET_TON"],
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

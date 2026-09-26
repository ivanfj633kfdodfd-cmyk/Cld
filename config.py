import os
from dotenv import load_dotenv

load_dotenv()

# ── Bot ────────────────────────────────────────────────────────────────────────
BOT_TOKEN: str = os.environ["BOT_TOKEN"]
ADMIN_ID: int  = int(os.environ["ADMIN_ID"])
BOT_USERNAME: str = os.getenv("BOT_USERNAME", "")  # e.g. "ClaudeSubBot"

# ── Webhook ────────────────────────────────────────────────────────────────────
WEBHOOK_HOST: str = os.getenv("WEBHOOK_HOST", "")
WEBHOOK_PATH: str = os.getenv("WEBHOOK_PATH", "/webhook")
WEBHOOK_URL:  str = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# ── Crypto wallets ─────────────────────────────────────────────────────────────
_PLACEHOLDER = "Address not configured yet"

WALLETS: dict[str, dict] = {
    "USDT TRC-20": {
        "address": os.getenv("WALLET_USDT_TRC20", _PLACEHOLDER),
        "network": "TRON (TRC-20)",
    },
    "USDT ERC-20": {
        "address": os.getenv("WALLET_USDT_ERC20", _PLACEHOLDER),
        "network": "Ethereum (ERC-20)",
    },
    "USDC ERC-20": {
        "address": os.getenv("WALLET_USDC_ERC20", _PLACEHOLDER),
        "network": "Ethereum (ERC-20)",
    },
    "TRX": {
        "address": os.getenv("WALLET_TRON", _PLACEHOLDER),
        "network": "TRON",
    },
    "BTC": {
        "address": os.getenv("WALLET_BTC", _PLACEHOLDER),
        "network": "Bitcoin",
    },
    "ETH": {
        "address": os.getenv("WALLET_ETH", _PLACEHOLDER),
        "network": "Ethereum",
    },
    "BNB": {
        "address": os.getenv("WALLET_BNB", _PLACEHOLDER),
        "network": "BNB Smart Chain (BEP-20)",
    },
    "SOL": {
        "address": os.getenv("WALLET_SOL", _PLACEHOLDER),
        "network": "Solana",
    },
    "TON": {
        "address": os.getenv("WALLET_TON", _PLACEHOLDER),
        "network": "TON",
    },
}

# ── Plans (official claude.com/pricing) ───────────────────────────────────────
#
# Claude Pro   — $20/month
# Claude Max 5x  — $100/month
# Claude Max 20x — $200/month
#
PLANS: dict[str, dict] = {
    "pro": {
        "label":     "Claude Pro",
        "price_usd": 20,
        "per_month": 20,
        "saving":    None,
        "badge":     None,
        "features": [
            "Everything in Free",
            "5× more usage than Free",
            "Claude Code included",
            "Claude Design, Slides, Docs",
            "Claude Science",
            "Projects",
            "All models: Sonnet 5, Opus 5, Haiku",
            "Priority access at peak times",
        ],
    },
    "max_5x": {
        "label":     "Claude Max 5×",
        "price_usd": 100,
        "per_month": 100,
        "saving":    None,
        "badge":     "Popular",
        "features": [
            "Everything in Pro",
            "5× more usage than Pro",
            "Higher output limits",
            "Early access to new features",
            "Priority access at all times",
        ],
    },
    "max_20x": {
        "label":     "Claude Max 20×",
        "price_usd": 200,
        "per_month": 200,
        "saving":    None,
        "badge":     "Power users",
        "features": [
            "Everything in Pro",
            "20× more usage than Pro",
            "Highest output limits",
            "Early access to new features",
            "Priority access at all times",
        ],
    },
}

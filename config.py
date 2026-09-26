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

# ── Plans (based on claude.com/pricing) ───────────────────────────────────────
#
# Claude Pro  — $20/month
# We offer 1, 3, 6, 12 month packs at the same per-month rate.
# Savings are applied as a discount on multi-month packs.
#
PLANS: dict[str, dict] = {
    "pro_1m": {
        "label":     "Claude Pro — 1 month",
        "price_usd": 20,
        "per_month": 20,
        "saving":    None,
        "badge":     None,
        "features": [
            "Everything in Free",
            "More usage limits",
            "Claude Code included",
            "Claude Design, Slides, Docs",
            "Claude Science",
            "Projects",
            "All Claude models (Sonnet, Opus, Haiku)",
            "Priority access at high traffic",
        ],
    },
    "pro_3m": {
        "label":     "Claude Pro — 3 months",
        "price_usd": 54,
        "per_month": 18,
        "saving":    "Save $6",
        "badge":     "Popular",
        "features": [
            "Everything in Free",
            "More usage limits",
            "Claude Code included",
            "Claude Design, Slides, Docs",
            "Claude Science",
            "Projects",
            "All Claude models (Sonnet, Opus, Haiku)",
            "Priority access at high traffic",
        ],
    },
    "pro_6m": {
        "label":     "Claude Pro — 6 months",
        "price_usd": 102,
        "per_month": 17,
        "saving":    "Save $18",
        "badge":     "Best value",
        "features": [
            "Everything in Free",
            "More usage limits",
            "Claude Code included",
            "Claude Design, Slides, Docs",
            "Claude Science",
            "Projects",
            "All Claude models (Sonnet, Opus, Haiku)",
            "Priority access at high traffic",
        ],
    },
    "pro_12m": {
        "label":     "Claude Pro — 12 months",
        "price_usd": 200,
        "per_month": 17,
        "saving":    "Save $40",
        "badge":     "Annual",
        "features": [
            "Everything in Free",
            "More usage limits",
            "Claude Code included",
            "Claude Design, Slides, Docs",
            "Claude Science",
            "Projects",
            "All Claude models (Sonnet, Opus, Haiku)",
            "Priority access at high traffic",
        ],
    },
}

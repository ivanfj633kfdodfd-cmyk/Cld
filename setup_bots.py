"""
setup_bots.py — full automation: create Vercel project, copy env vars,
                 deploy, register Telegram webhook.

Requirements:
    pip install httpx

Config:
    1. Fill VERCEL_TOKEN  (vercel.com/account/tokens)
    2. Fill VERCEL_TEAM   (your team slug, e.g. "names-projects" — from URL)
    3. Fill SOURCE_PROJECT_ID  (ID of your existing working project)
    4. Fill GITHUB_REPO   (e.g. "ivanfj633kfdodfd-cmyk/Cld")
    5. Fill BOTS list below

Run:
    python setup_bots.py
"""

import httpx
import time
import sys
import os
from dotenv import load_dotenv

load_dotenv()

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG — fill .env file, not here
# ══════════════════════════════════════════════════════════════════════════════

VERCEL_TOKEN      = os.getenv("VERCEL_TOKEN", "")
VERCEL_TEAM_ID    = os.getenv("VERCEL_TEAM_ID", "")
SOURCE_PROJECT_ID = os.getenv("SOURCE_PROJECT_ID", "")
GITHUB_REPO       = "ivanfj633kfdodfd-cmyk/Cld"  # org/repo
GITHUB_BRANCH     = "main"

# List of bots to create.
# Each entry: (project_name, bot_token, bot_username)
BOTS = [
    # ("cld-bot2", "7XXXXXXXXX:AAH...", "ClaudeBot2"),
    # ("cld-bot3", "7XXXXXXXXX:AAH...", "ClaudeBot3"),
]

WEBHOOK_PATH = "/webhook"
ADMIN_ID     = ""   # your Telegram user ID — same for all bots

# ══════════════════════════════════════════════════════════════════════════════

V_API = "https://api.vercel.com"

def vheaders():
    return {"Authorization": f"Bearer {VERCEL_TOKEN}"}

def team_param():
    return {"teamId": VERCEL_TEAM_ID} if VERCEL_TEAM_ID else {}


def get_env_vars(project_id: str) -> list[dict]:
    """Fetch all env vars from source project."""
    r = httpx.get(
        f"{V_API}/v9/projects/{project_id}/env",
        headers=vheaders(), params=team_param(), timeout=10
    )
    return r.json().get("envs", [])


def create_project(name: str) -> dict:
    """Create new Vercel project linked to GitHub repo."""
    payload = {
        "name": name,
        "framework": "flask",
        "gitRepository": {
            "type": "github",
            "repo": GITHUB_REPO,
        },
    }
    r = httpx.post(
        f"{V_API}/v10/projects",
        headers=vheaders(), params=team_param(),
        json=payload, timeout=15
    )
    return r.json()


def copy_env_vars(target_project_id: str, source_envs: list[dict],
                  overrides: dict) -> None:
    """Copy env vars to new project, applying overrides."""
    envs_to_set = []
    for e in source_envs:
        key   = e["key"]
        value = overrides.get(key, e.get("decryptedValue") or e.get("value", ""))
        if not value:
            continue
        envs_to_set.append({
            "key":    key,
            "value":  value,
            "type":   e.get("type", "encrypted"),
            "target": e.get("target", ["production", "preview", "development"]),
        })

    # Add any overrides that aren't in source
    existing_keys = {e["key"] for e in source_envs}
    for key, value in overrides.items():
        if key not in existing_keys and value:
            envs_to_set.append({
                "key":    key,
                "value":  value,
                "type":   "encrypted",
                "target": ["production", "preview", "development"],
            })

    r = httpx.post(
        f"{V_API}/v10/projects/{target_project_id}/env",
        headers=vheaders(), params=team_param(),
        json=envs_to_set, timeout=15
    )
    if not r.json().get("created") and r.status_code >= 400:
        print(f"    [warn] env vars response: {r.status_code} {r.text[:200]}")


def trigger_deploy(project_id: str) -> str | None:
    """Trigger a deployment and return deployment URL."""
    r = httpx.post(
        f"{V_API}/v13/deployments",
        headers=vheaders(), params=team_param(),
        json={
            "name":   project_id,
            "gitSource": {
                "type":   "github",
                "repo":   GITHUB_REPO,
                "ref":    GITHUB_BRANCH,
            },
        },
        timeout=20
    )
    data = r.json()
    return data.get("url")


def wait_for_deploy(project_id: str, max_wait: int = 120) -> str | None:
    """Poll until deployment is ready, return production URL."""
    print("    Waiting for deploy", end="", flush=True)
    for _ in range(max_wait // 5):
        time.sleep(5)
        r = httpx.get(
            f"{V_API}/v9/projects/{project_id}",
            headers=vheaders(), params=team_param(), timeout=10
        )
        data = r.json()
        domains = data.get("targets", {}).get("production", {}).get("alias", [])
        if domains:
            print(" done")
            return f"https://{domains[0]}"
        print(".", end="", flush=True)
    print(" timeout")
    return None


def set_webhook(token: str, url: str) -> bool:
    r = httpx.post(
        f"https://api.telegram.org/bot{token}/setWebhook",
        json={"url": f"{url}{WEBHOOK_PATH}",
              "allowed_updates": ["message", "callback_query"]},
        timeout=10
    )
    return r.json().get("ok", False)


def get_me(token: str) -> dict | None:
    r = httpx.get(f"https://api.telegram.org/bot{token}/getMe", timeout=8)
    data = r.json()
    return data.get("result") if data.get("ok") else None


# ══════════════════════════════════════════════════════════════════════════════

def main():
    if not VERCEL_TOKEN:
        print("ERROR: Set VERCEL_TOKEN in the script.")
        sys.exit(1)
    if not BOTS:
        print("ERROR: Add bots to the BOTS list.")
        sys.exit(1)
    if not SOURCE_PROJECT_ID:
        print("ERROR: Set SOURCE_PROJECT_ID.")
        sys.exit(1)

    print(f"Fetching env vars from source project {SOURCE_PROJECT_ID}...")
    source_envs = get_env_vars(SOURCE_PROJECT_ID)
    print(f"  Found {len(source_envs)} env vars\n")

    for i, (proj_name, bot_token, bot_username) in enumerate(BOTS):
        print(f"[{i+1}/{len(BOTS)}] {proj_name} (@{bot_username})")

        # Validate token
        info = get_me(bot_token)
        if not info:
            print("  [SKIP] Invalid token\n")
            continue
        print(f"  Bot: @{info.get('username')} — {info.get('first_name')}")

        # Create project
        print("  Creating Vercel project...")
        proj = create_project(proj_name)
        if "error" in proj:
            print(f"  [ERROR] {proj['error'].get('message')}\n")
            continue
        proj_id = proj["id"]
        print(f"  Project ID: {proj_id}")

        # Copy env vars with overrides
        overrides = {
            "BOT_TOKEN":    bot_token,
            "BOT_USERNAME": bot_username,
        }
        if ADMIN_ID:
            overrides["ADMIN_ID"] = ADMIN_ID
        print("  Copying env vars...")
        copy_env_vars(proj_id, source_envs, overrides)

        # Deploy
        print("  Triggering deployment...")
        trigger_deploy(proj_id)
        prod_url = wait_for_deploy(proj_id)

        if not prod_url:
            print("  [WARN] Could not detect production URL. Register webhook manually.\n")
            continue

        print(f"  URL: {prod_url}")

        # Register webhook
        ok = set_webhook(bot_token, prod_url)
        if ok:
            print(f"  [OK] Webhook registered → {prod_url}{WEBHOOK_PATH}")
        else:
            print(f"  [FAIL] Webhook registration failed. Run manually:")
            print(f"    https://api.telegram.org/bot{bot_token}/setWebhook?url={prod_url}{WEBHOOK_PATH}")
        print()

    print("All done.")


if __name__ == "__main__":
    main()

"""
fix_env.py — copy missing env vars from source project to all clone projects
             and trigger redeploy.

Run: python fix_env.py
"""

import httpx
import os
from dotenv import load_dotenv

load_dotenv()

VERCEL_TOKEN      = os.getenv("VERCEL_TOKEN", "")
VERCEL_TEAM_ID    = os.getenv("VERCEL_TEAM_ID", "")
SOURCE_PROJECT_ID = os.getenv("SOURCE_PROJECT_ID", "")
GITHUB_REPO       = "ivanfj633kfdodfd-cmyk/Cld"

# Projects to fix — IDs from the setup_bots.py output
TARGET_PROJECTS = [
    "cld-claude-1",
    "cld-claude-2",
    "cld-claude-3",
    "cld-claude-4",
]

V_API = "https://api.vercel.com"

def headers():
    return {"Authorization": f"Bearer {VERCEL_TOKEN}"}

def team():
    return {"teamId": VERCEL_TEAM_ID} if VERCEL_TEAM_ID else {}


def get_project_id(name: str) -> str | None:
    r = httpx.get(f"{V_API}/v9/projects/{name}",
                  headers=headers(), params=team(), timeout=10)
    d = r.json()
    return d.get("id")


def get_env_vars(project_id: str) -> list[dict]:
    r = httpx.get(f"{V_API}/v9/projects/{project_id}/env",
                  headers=headers(), params=team(), timeout=10)
    return r.json().get("envs", [])


def get_existing_keys(project_id: str) -> set[str]:
    return {e["key"] for e in get_env_vars(project_id)}


def add_env_var(project_id: str, key: str, value: str) -> bool:
    r = httpx.post(
        f"{V_API}/v10/projects/{project_id}/env",
        headers=headers(), params=team(),
        json=[{
            "key":    key,
            "value":  value,
            "type":   "encrypted",
            "target": ["production", "preview", "development"],
        }],
        timeout=10
    )
    return r.status_code < 400


def redeploy(project_id: str) -> bool:
    r = httpx.post(
        f"{V_API}/v13/deployments",
        headers=headers(), params=team(),
        json={
            "name": project_id,
            "gitSource": {
                "type": "github",
                "repo": GITHUB_REPO,
                "ref":  "main",
            },
        },
        timeout=15
    )
    return r.status_code < 400


def main():
    if not VERCEL_TOKEN or not SOURCE_PROJECT_ID:
        print("Set VERCEL_TOKEN and SOURCE_PROJECT_ID in .env")
        return

    print(f"Fetching env vars from source {SOURCE_PROJECT_ID}...")
    source_envs = get_env_vars(SOURCE_PROJECT_ID)

    # Keys to skip — these are already set per-bot
    skip_keys = {"BOT_TOKEN", "BOT_USERNAME", "WEBHOOK_HOST"}

    print(f"Found {len(source_envs)} vars in source\n")

    for name in TARGET_PROJECTS:
        print(f"Processing {name}...")
        proj_id = get_project_id(name)
        if not proj_id:
            print(f"  [ERROR] Project not found\n")
            continue
        print(f"  ID: {proj_id}")

        existing = get_existing_keys(proj_id)
        added = 0

        for env in source_envs:
            key = env["key"]
            if key in skip_keys or key in existing:
                continue
            value = env.get("decryptedValue") or env.get("value", "")
            if not value:
                print(f"  [skip] {key} — no value (encrypted, add manually)")
                continue
            ok = add_env_var(proj_id, key, value)
            if ok:
                print(f"  [+] {key}")
                added += 1
            else:
                print(f"  [!] {key} — failed")

        print(f"  Added {added} vars")

        print(f"  Triggering redeploy...")
        ok = redeploy(proj_id)
        print(f"  Redeploy: {'OK' if ok else 'FAILED'}\n")

    print("Done. Check Vercel for deployment status.")


if __name__ == "__main__":
    main()

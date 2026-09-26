"""
In-memory FSM store.
Vercel serverless instances are ephemeral — state lives only within one warm instance.
For production, swap _store with Redis (upstash.com free tier works great).
"""
from __future__ import annotations

_state: dict[int, str]       = {}
_data:  dict[int, dict]      = {}


def get_state(user_id: int) -> str | None:
    return _state.get(user_id)


def set_state(user_id: int, state: str) -> None:
    _state[user_id] = state


def get_data(user_id: int) -> dict:
    return _data.get(user_id, {})


def set_data(user_id: int, data: dict) -> None:
    _data[user_id] = data


def clear_state(user_id: int) -> None:
    _state.pop(user_id, None)
    _data.pop(user_id, None)

"""Deterministic local user/session boundary helpers for v1.42 evidence."""
from __future__ import annotations

from typing import Any


VERSION = "v1.42"
SCHEMA_VERSION = "local_session_boundary.v1"
NOW = "2026-06-24T00:00:00Z"
EXPIRES = "2026-06-24T02:00:00Z"

USER_A = {
    "local_user_fixture_id": "user_fixture_A",
    "local_user_id": "local_user_A",
    "fixture_persona": "office_daily_minimal",
    "memory_namespace_id": "mem_ns_local_user_A",
    "governance_namespace_id": "gov_ns_local_user_A",
    "closet_namespace_id": "closet_ns_local_user_A",
    "allowed_session_ids": ["sess_A_001", "sess_A_002"],
    "source_v141_case_refs": [],
    "trace_refs": ["local_user_A", "mem_ns_local_user_A", "gov_ns_local_user_A"],
}
USER_B = {
    "local_user_fixture_id": "user_fixture_B",
    "local_user_id": "local_user_B",
    "fixture_persona": "office_daily_color",
    "memory_namespace_id": "mem_ns_local_user_B",
    "governance_namespace_id": "gov_ns_local_user_B",
    "closet_namespace_id": "closet_ns_local_user_B",
    "allowed_session_ids": ["sess_B_001"],
    "source_v141_case_refs": [],
    "trace_refs": ["local_user_B", "mem_ns_local_user_B", "gov_ns_local_user_B"],
}
USERS = {"local_user_A": USER_A, "local_user_B": USER_B}


def local_user_fixtures() -> list[dict[str, Any]]:
    return [dict(USER_A), dict(USER_B)]


def session_envelope(user_id: str, session_id: str, state_version: int = 1, status: str = "active") -> dict[str, Any]:
    return {
        "local_session_envelope_id": f"session_env_{session_id}",
        "version": VERSION,
        "schema_version": SCHEMA_VERSION,
        "local_user_id": user_id,
        "local_session_id": session_id,
        "session_state_version": state_version,
        "session_status": status,
        "request_context": "office_daily",
        "session_started_at": NOW,
        "expires_at": EXPIRES,
        "trace_refs": [user_id, session_id, f"session_state_v{state_version}"],
    }


def user_state_namespace(user_id: str, session_id: str) -> dict[str, Any]:
    fixture = USERS[user_id]
    return {
        "user_state_namespace_id": f"state_ns_{user_id}_{session_id}",
        "local_user_id": user_id,
        "local_session_id": session_id,
        "memory_namespace_id": fixture["memory_namespace_id"],
        "governance_namespace_id": fixture["governance_namespace_id"],
        "closet_namespace_id": fixture["closet_namespace_id"],
        "action_namespace_id": f"action_ns_{session_id}",
        "idempotency_namespace_id": f"idem_ns_{session_id}",
        "snapshot_namespace_id": f"snap_ns_{session_id}",
        "trace_refs": [user_id, session_id, fixture["memory_namespace_id"], fixture["governance_namespace_id"]],
    }


def trace_safe_debug_ref(user_id: str, session_id: str, case_id: str) -> dict[str, Any]:
    return {
        "trace_safe_debug_ref_id": f"debug_{case_id}",
        "local_user_id": user_id,
        "local_session_id": session_id,
        "debug_ref": f"trace:v142:{user_id}:{session_id}:{case_id}",
        "filesystem_path_exposed": False,
        "foreign_user_or_session_exposed": False,
        "trace_refs": [user_id, session_id, case_id],
    }


def scoped_idempotency_key(user_id: str, session_id: str, route: str, card_id: str | None, idem: str | None) -> str:
    return f"{user_id}:{session_id}:{route}:{card_id or 'no_card'}:{idem or 'no_idempotency_key'}"


def foreign_tokens(user_id: str, session_id: str) -> dict[str, set[str]]:
    foreign_users = {uid for uid in USERS if uid != user_id}
    all_sessions = {"sess_A_001", "sess_A_002", "sess_B_001"}
    foreign_sessions = all_sessions - {session_id}
    foreign_namespaces: set[str] = set()
    for uid, fixture in USERS.items():
        if uid == user_id:
            continue
        foreign_namespaces.update({fixture["memory_namespace_id"], fixture["governance_namespace_id"], fixture["closet_namespace_id"]})
    for sid in foreign_sessions:
        foreign_namespaces.update({f"action_ns_{sid}", f"idem_ns_{sid}", f"snap_ns_{sid}"})
    return {"users": foreign_users, "sessions": foreign_sessions, "namespaces": foreign_namespaces}


def collect_string_values(value: Any) -> list[str]:
    if isinstance(value, dict):
        out: list[str] = []
        for item in value.values():
            out.extend(collect_string_values(item))
        return out
    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(collect_string_values(item))
        return out
    if isinstance(value, str):
        return [value]
    return []


def leakage_scan(value: Any, user_id: str, session_id: str) -> dict[str, list[str]]:
    strings = collect_string_values(value)
    tokens = foreign_tokens(user_id, session_id)
    return {
        "foreign_user_refs_detected": sorted({token for token in tokens["users"] if any(token in text for text in strings)}),
        "foreign_session_refs_detected": sorted({token for token in tokens["sessions"] if any(token in text for text in strings)}),
        "foreign_namespace_refs_detected": sorted({token for token in tokens["namespaces"] if any(token in text for text in strings)}),
    }

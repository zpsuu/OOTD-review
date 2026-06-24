"""Deterministic helpers for v1.43 product conversation loop evidence."""
from __future__ import annotations

import copy
from typing import Any

from benchmark.benchmark_v142.session.local_session_boundary import USERS as V142_USERS
from benchmark.common.raw_artifact_validation import canonical_json_hash


VERSION = "v1.43"
NOW = "2026-06-24T00:00:00Z"
USERS = copy.deepcopy(V142_USERS)
CONVERSATION_IDS = {"conv_A_001", "conv_A_002", "conv_B_001"}
FORBIDDEN_VISIBLE_TERMS = {
    "raw_evidence",
    "risk_reasons",
    "internal_only",
    "/ssd2/",
    "traceback",
    "global memory",
    "globalize",
    "body",
    "identity",
    "attractive",
    "sku",
    "merchant",
    "affiliate",
    "aigc",
    "image generation",
}


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


def foreign_tokens(user_id: str, session_id: str, conversation_id: str) -> dict[str, set[str]]:
    users = {uid for uid in USERS if uid != user_id}
    sessions = {"sess_A_001", "sess_A_002", "sess_B_001"} - {session_id}
    conversations = CONVERSATION_IDS - {conversation_id}
    namespaces: set[str] = set()
    for uid, fixture in USERS.items():
        if uid != user_id:
            namespaces.update(
                {
                    fixture["memory_namespace_id"],
                    fixture["governance_namespace_id"],
                    fixture["closet_namespace_id"],
                }
            )
    for sid in sessions:
        namespaces.update({f"action_ns_{sid}", f"idem_ns_{sid}", f"snap_ns_{sid}"})
    return {
        "users": users,
        "sessions": sessions,
        "conversations": conversations,
        "namespaces": namespaces,
    }


def leakage_scan(value: Any, user_id: str, session_id: str, conversation_id: str) -> dict[str, list[str]]:
    strings = collect_string_values(value)
    tokens = foreign_tokens(user_id, session_id, conversation_id)
    return {
        "foreign_user_refs_detected": sorted({token for token in tokens["users"] if any(token in text for text in strings)}),
        "foreign_session_refs_detected": sorted({token for token in tokens["sessions"] if any(token in text for text in strings)}),
        "foreign_conversation_refs_detected": sorted({token for token in tokens["conversations"] if any(token in text for text in strings)}),
        "foreign_namespace_refs_detected": sorted({token for token in tokens["namespaces"] if any(token in text for text in strings)}),
    }


def scoped_idempotency_key(user_id: str, session_id: str, conversation_id: str, action_card_id: str, raw_key: str) -> str:
    return f"{user_id}:{session_id}:{conversation_id}:{action_card_id}:{raw_key}"


def conversation_state(user_id: str, session_id: str, conversation_id: str, turn_id: str, accepted_refs: list[str] | None = None) -> dict[str, Any]:
    return {
        "local_user_id": user_id,
        "local_session_id": session_id,
        "conversation_id": conversation_id,
        "turn_id": turn_id,
        "memory_namespace_id": USERS[user_id]["memory_namespace_id"],
        "governance_namespace_id": USERS[user_id]["governance_namespace_id"],
        "accepted_action_result_refs": list(accepted_refs or []),
    }


def state_hash(state: dict[str, Any]) -> str:
    return canonical_json_hash(state)


def visible_text_has_forbidden_terms(value: Any) -> list[str]:
    joined = "\n".join(collect_string_values(value)).lower()
    return sorted(term for term in FORBIDDEN_VISIBLE_TERMS if term in joined)

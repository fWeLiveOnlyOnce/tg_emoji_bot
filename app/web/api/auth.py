from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl


class MiniAppAuthError(ValueError):
    pass


@dataclass(slots=True, frozen=True)
class TelegramMiniAppUser:
    id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    language_code: str | None
    is_premium: bool | None


@dataclass(slots=True, frozen=True)
class TelegramInitData:
    query_id: str | None
    auth_date: int
    user: TelegramMiniAppUser
    raw: str


def _build_secret_key(bot_token: str) -> bytes:
    if not bot_token or not isinstance(bot_token, str):
        raise MiniAppAuthError("Bot token is not configured")
    return hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()


def _parse_init_data_pairs(init_data_raw: str) -> list[tuple[str, str]]:
    if not init_data_raw or not isinstance(init_data_raw, str):
        raise MiniAppAuthError("init_data is empty")

    if len(init_data_raw) > 8192:
        raise MiniAppAuthError("init_data is too large")

    pairs = parse_qsl(
        init_data_raw,
        keep_blank_values=True,
        strict_parsing=True,
        encoding="utf-8",
        errors="strict",
    )

    if not pairs:
        raise MiniAppAuthError("init_data has no fields")

    return pairs


def _extract_hash_and_data_check_string(pairs: list[tuple[str, str]]) -> tuple[str, str, dict[str, str]]:
    data: dict[str, str] = {}
    received_hash: str | None = None

    for key, value in pairs:
        if key == "hash":
            if received_hash is not None:
                raise MiniAppAuthError("Duplicate hash field")
            received_hash = value
            continue

        if key in data:
            raise MiniAppAuthError(f"Duplicate field: {key}")

        data[key] = value

    if not received_hash:
        raise MiniAppAuthError("Missing hash field")

    data_check_string = "\n".join(
        f"{key}={data[key]}"
        for key in sorted(data.keys())
    )

    return received_hash, data_check_string, data


def _validate_hash(received_hash: str, data_check_string: str, bot_token: str) -> None:
    secret_key = _build_secret_key(bot_token)
    expected_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise MiniAppAuthError("Invalid init_data signature")


def _validate_auth_date(auth_date_raw: str, max_age_seconds: int) -> int:
    try:
        auth_date = int(auth_date_raw)
    except (TypeError, ValueError) as exc:
        raise MiniAppAuthError("Invalid auth_date") from exc

    now = int(time.time())

    if auth_date > now + 30:
        raise MiniAppAuthError("auth_date is in the future")

    if now - auth_date > max_age_seconds:
        raise MiniAppAuthError("init_data is expired")

    return auth_date


def _parse_user(user_raw: str) -> TelegramMiniAppUser:
    try:
        user_obj = json.loads(user_raw)
    except json.JSONDecodeError as exc:
        raise MiniAppAuthError("Invalid user payload") from exc

    if not isinstance(user_obj, dict):
        raise MiniAppAuthError("User payload must be an object")

    user_id = user_obj.get("id")
    if not isinstance(user_id, int) or user_id <= 0:
        raise MiniAppAuthError("Invalid user id")

    username = user_obj.get("username")
    first_name = user_obj.get("first_name")
    last_name = user_obj.get("last_name")
    language_code = user_obj.get("language_code")
    is_premium = user_obj.get("is_premium")

    if username is not None and not isinstance(username, str):
        raise MiniAppAuthError("Invalid username")
    if first_name is not None and not isinstance(first_name, str):
        raise MiniAppAuthError("Invalid first_name")
    if last_name is not None and not isinstance(last_name, str):
        raise MiniAppAuthError("Invalid last_name")
    if language_code is not None and not isinstance(language_code, str):
        raise MiniAppAuthError("Invalid language_code")
    if is_premium is not None and not isinstance(is_premium, bool):
        raise MiniAppAuthError("Invalid is_premium flag")

    return TelegramMiniAppUser(
        id=user_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        language_code=language_code,
        is_premium=is_premium,
    )


def validate_telegram_init_data(
    init_data_raw: str,
    bot_token: str,
    *,
    max_age_seconds: int = 3600,
) -> TelegramInitData:
    pairs = _parse_init_data_pairs(init_data_raw)
    received_hash, data_check_string, data = _extract_hash_and_data_check_string(pairs)

    _validate_hash(received_hash, data_check_string, bot_token)

    auth_date_raw = data.get("auth_date")
    if auth_date_raw is None:
        raise MiniAppAuthError("Missing auth_date")

    auth_date = _validate_auth_date(auth_date_raw, max_age_seconds)

    user_raw = data.get("user")
    if user_raw is None:
        raise MiniAppAuthError("Missing user")

    user = _parse_user(user_raw)

    query_id = data.get("query_id")

    return TelegramInitData(
        query_id=query_id,
        auth_date=auth_date,
        user=user,
        raw=init_data_raw,
    )


def build_user_display_name(user: TelegramMiniAppUser) -> str:
    if user.username:
        return f"@{user.username}"

    full_name = " ".join(
        part for part in (user.first_name, user.last_name) if part
    ).strip()

    if full_name:
        return full_name

    return f"id:{user.id}"
from pathlib import Path
import logging
import os
import asyncio

from dotenv import load_dotenv
from telethon import TelegramClient

logger = logging.getLogger(__name__)


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Не найдена переменная окружения: {name}")
    return value


async def main():
    load_dotenv()

    api_id = int(require_env("API_ID"))
    api_hash = require_env("API_HASH")
    phone_number = require_env("PHONE_NUMBER")
    session_path = require_env("TELETHON_SESSION_PATH")

    session_file = Path(f"{session_path}.session")
    session_file.parent.mkdir(parents=True, exist_ok=True)

    print("[WAIT] Запускаю авторизацию Telethon...", flush=True)
    logger.debug("Session path: %s", session_file)

    client = TelegramClient(session_path, api_id, api_hash)
    await client.start(phone=phone_number)

    me = await client.get_me()
    print("[OK] Авторизация Telethon прошла успешно.", flush=True)
    logger.debug("Authorized user id=%s (@%s)", me.id, me.username)
    logger.debug("Session stored at: %s", session_file)

    await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[ERROR] {e}", flush=True)
        raise
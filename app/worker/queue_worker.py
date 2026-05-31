from __future__ import annotations

import asyncio
import os
import shutil
import socket
from pathlib import Path

from app.core.config import ensure_runtime_dirs, load_settings
from app.core.logging_config import setup_logging
from app.db.repository import (
    claim_next_queued_job,
    mark_job_done,
    mark_job_failed,
)
from app.services.converter import convert_job_to_tiles, ConversionError
from app.services.storage import remove_job_input_dir
from app.services.telegram_publisher import (
    create_custom_emoji_pack,
    add_tiles_to_existing_pack,
)

logger = setup_logging()

POLL_INTERVAL_SECONDS = 3


def worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


def remove_job_output_dir(base_output_dir: Path, public_id: str) -> None:
    job_dir = (base_output_dir / public_id).resolve()

    if not job_dir.exists():
        return

    expected_root = base_output_dir.resolve()
    if job_dir.parent != expected_root:
        raise RuntimeError("Unsafe output cleanup path detected.")

    shutil.rmtree(job_dir)


def cleanup_job_dirs(settings, public_id: str) -> None:
    """Удаляет временные input/output каталоги задачи.

    Безопасно вызывать при любом исходе (успех или ошибка): сбои очистки
    только логируются и не валят обработку."""
    try:
        remove_job_input_dir(settings.input_dir, public_id)
        remove_job_output_dir(settings.output_dir, public_id)
    except Exception:
        logger.exception(f"Cleanup failed public_id={public_id}")


async def process_job(job) -> str:
    settings = load_settings()

    # Конвертация синхронная и тяжёлая — уводим её в поток, чтобы не блокировать loop.
    if job.target_short_name:
        # Добавление в существующий пак: имя фиксировано, уникализация не нужна.
        conversion = await asyncio.to_thread(
            convert_job_to_tiles, job, settings.output_dir
        )
        return await add_tiles_to_existing_pack(job, conversion)

    if not job.short_name:
        raise RuntimeError("job.short_name is empty")

    conversion = await asyncio.to_thread(
        convert_job_to_tiles, job, settings.output_dir
    )
    return await create_custom_emoji_pack(job, conversion)


async def main() -> None:
    settings = load_settings()
    ensure_runtime_dirs(settings)

    current_worker = worker_id()
    logger.info(f"Queue worker started: {current_worker}")

    while True:
        try:
            job = claim_next_queued_job()

            if job is None:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                continue

            logger.info(
                f"Claimed job public_id={job.public_id} "
                f"source_type={job.source_type} "
                f"title={job.title} short_name={job.short_name}"
            )

            try:
                pack_url = await process_job(job)
                mark_job_done(job.public_id, pack_url)
                logger.info(f"Job completed public_id={job.public_id} pack_url={pack_url}")
            except ConversionError as e:
                mark_job_failed(job.public_id, str(e))
                logger.warning(f"Job failed (conversion) public_id={job.public_id}: {e}")
            except Exception:
                mark_job_failed(job.public_id, "Внутренняя ошибка обработки. Попробуйте позже.")
                logger.exception(f"Job failed public_id={job.public_id}")
            finally:
                # R5: чистим временные файлы в любом исходе — и при успехе, и при ошибке.
                cleanup_job_dirs(settings, job.public_id)

        except Exception as outer_error:
            logger.exception(f"Worker loop error: {outer_error}")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
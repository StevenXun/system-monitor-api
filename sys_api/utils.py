import logging
import os
import subprocess
from datetime import datetime, timezone
from typing import Any

import redis
from fastapi import HTTPException


logger = logging.getLogger(__name__)


REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
COMMAND_TIMEOUT_SECONDS = int(os.getenv("COMMAND_TIMEOUT_SECONDS", "5"))


redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)


def now_ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_response(message: str, data: Any) -> dict[str, Any]:
    return {
        "message": message,
        "data": data,
        "timestamp": now_ts(),
    }


def build_error_response(message: str, error: Any) -> dict[str, Any]:
    return {
        "message": message,
        "data": None,
        "error": error,
        "timestamp": now_ts(),
    }


def run_command(command: list[str]) -> str:
    command_display = " ".join(command)

    try:
        logger.info("running command: %s", command_display)

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )

        return result.stdout

    except subprocess.TimeoutExpired as exc:
        logger.error("command timed out: %s", command_display)

        raise HTTPException(
            status_code=500,
            detail=f"command timed out: {command_display}",
        ) from exc

    except subprocess.CalledProcessError as exc:
        error_output = exc.stderr.strip() or exc.stdout.strip() or str(exc)

        logger.error(
            "command failed: %s - %s",
            command_display,
            error_output,
        )

        raise HTTPException(
            status_code=500,
            detail=f"command failed: {error_output}",
        ) from exc

    except OSError as exc:
        logger.error(
            "command not available: %s - %s",
            command_display,
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail=f"command not available: {command[0]}",
        ) from exc

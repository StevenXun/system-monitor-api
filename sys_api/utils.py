import subprocess
from datetime import datetime, timezone
from fastapi import HTTPException
import logging
import redis


redis_client = redis.Redis(
    host="redis",
    port=6379,
    decode_responses=True
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def now_ts():
    return datetime.now(timezone.utc).isoformat()


def build_response(message, data):
    return {
        "message": message,
        "data": data,
        "timestamp": now_ts()
    }


def build_error_response(message, error):
    return {
        "message": message,
        "data": None,
        "error": error,
        "timestamp": now_ts()
    }


def run_command(command):
    try:
        logger.info(f"running command: {' '.join(command)}")
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except Exception as e:
        logger.error(f"command failed: {' '.join(command)} - {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"command failed: {str(e)}"
        )

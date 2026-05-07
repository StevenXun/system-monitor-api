import logging
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from sys_api.logging_config import setup_logging
from sys_api.routes.metrics import router
from sys_api.utils import build_error_response


setup_logging()
logger = logging.getLogger(__name__)


app = FastAPI(
    title="System Monitor API",
    version="1.0.0",
    description="A FastAPI-based system monitoring API for CPU, memory, disk, "
    "and uptime metrics.",
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_response("request failed", exc.detail),
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    try:
        response = await call_next(request)
    except Exception:
        process_time = time.time() - start_time

        logger.exception(
            "%s %s - request failed - %.4fs",
            request.method,
            request.url.path,
            process_time,
        )

        raise

    process_time = time.time() - start_time

    logger.info(
        "%s %s - %s - %.4fs",
        request.method,
        request.url.path,
        response.status_code,
        process_time,
    )

    return response


app.include_router(router)

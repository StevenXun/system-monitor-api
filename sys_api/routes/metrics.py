from fastapi import APIRouter, Query

from sys_api.services.system_metrics import (
    get_cpu_metrics,
    get_disk_metrics,
    get_memory_metrics,
    get_uptime_metrics,
)
from sys_api.utils import build_response, logger

router = APIRouter()


@router.get("/health")
def health_check():
    logger.info("received health request")
    return build_response("service is healthy", {"status": "ok"})


@router.get("/info")
def get_info():
    logger.info("received info request")
    return build_response(
        "service info",
        {
            "service_name": "system-monitor-api",
            "version": "1.0.0",
        },
    )


@router.get("/disk")
def get_disk(
    min_usage: int = Query(0, ge=0, le=100),
    top_n: int | None = Query(None, ge=1),
):
    logger.info(
        "received disk request with min_usage=%s, top_n=%s",
        min_usage,
        top_n,
    )
    results = get_disk_metrics(min_usage, top_n)
    return build_response("disk info fetched successfully", results)


@router.get("/memory")
def get_memory():
    logger.info("received memory request")
    results = get_memory_metrics()
    return build_response("memory info fetched successfully", results)


@router.get("/cpu")
def get_cpu():
    logger.info("received cpu request")
    results = get_cpu_metrics()
    return build_response("cpu info fetched successfully", results)


@router.get("/uptime")
def get_uptime():
    logger.info("received uptime request")
    results = get_uptime_metrics()
    return build_response("uptime info fetched successfully", results)

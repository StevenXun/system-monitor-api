from fastapi import APIRouter, Query
import json
from datetime import datetime, timezone
from redis.exceptions import RedisError
import logging
from sys_api.services.system_metrics import (
    get_cpu_metrics,
    get_disk_metrics,
    get_memory_metrics,
    get_uptime_metrics,
)
from sys_api.utils import redis_client, now_ts, build_response

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/")
def root():
    return build_response("system monitor api", {"status": "running"})


@router.get("/visits")
def get_visits():
    count = 0

    try:
        value = redis_client.get("health_visits")
        if value is not None:
            count = int(value)
    except RedisError as e:
        logger.warning("redis unavailable while fetching visits: %s", e)

    return build_response(
        "visit count fetched successfully",
        {"health_visits": count},
    )


@router.get("/redis-test")
def redis_test():
    value = None

    try:
        redis_client.set("service_name", "system-monitor-api")
        value = redis_client.get("service_name")
    except RedisError as e:
        logger.warning("redis unavailable in redis-test: %s", e)

    return build_response("redis test ok", {"service_name": value})


@router.get("/health")
def health_check():
    try:
        redis_client.incr("health_visits")
    except RedisError as e:
        logger.warning("failed to increment health in redis: %s", e)
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
    cache_payload = {
        "cached_at": now_ts(),
        "disk_data": results,
    }

    try:
        old_data = redis_client.get("last_disk_metrics")
        should_record_history = True

        if old_data:
            old_payload = json.loads(old_data)
            if old_payload.get("disk_data") == results:
                should_record_history = False

        redis_client.set("last_disk_metrics", json.dumps(cache_payload))

        if should_record_history:
            redis_client.lpush("disk_history", json.dumps(cache_payload))
            redis_client.ltrim("disk_history", 0, 9)

    except RedisError as e:
        logger.warning("redis unavailable while caching disk metrics: %s", e)

    return build_response("disk info fetched successfully", results)


@router.get("/disk/last")
def get_last_disk():
    try:
        cached_data = redis_client.get("last_disk_metrics")
    except RedisError as e:
        logger.warning(
            "redis unavailable while fetching last disk metrics: %s",
            e
            )
        return build_response("no cached disk info found", {})

    if cached_data is None:
        return build_response("no cached disk info found", {})

    payload = json.loads(cached_data)

    if isinstance(payload, list):
        return build_response(
            "last disk info fetched successfully",
            {
                "cached_at": None,
                "cache_age_seconds": None,
                "disk_data": payload,
            },
        )

    cached_at_str = payload["cached_at"]
    cached_at_dt = datetime.fromisoformat(cached_at_str)
    now_dt = datetime.now(timezone.utc)
    cache_age_seconds = int((now_dt - cached_at_dt).total_seconds())

    return build_response(
        "last disk info fetched successfully",
        {
            "cached_at": cached_at_str,
            "cache_age_seconds": cache_age_seconds,
            "disk_data": payload["disk_data"],
        },
    )


@router.get("/disk/history")
def get_disk_history(limit: int = Query(5, ge=1, le=50)):
    try:
        raw_list = redis_client.lrange("disk_history", 0, limit - 1)
        history = [json.loads(item) for item in raw_list]
    except RedisError as e:
        logger.warning("redis unavailable while fetching disk history: %s", e)
        history = []

    return build_response(
        "disk history fetched successfully",
        {
            "count": len(history),
            "items": history,
        },
    )


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


@router.get("/metrics/summary")
def get_metrics_summary():
    logger.info("received metrics summary request")

    disk_data = get_disk_metrics(min_usage=0, top_n=None)
    memory_data = get_memory_metrics()
    cpu_data = get_cpu_metrics()

    return build_response(
        "metrics summary fetched successfully",
        {
            "disk": disk_data,
            "memory": memory_data,
            "cpu": cpu_data,
        },
    )

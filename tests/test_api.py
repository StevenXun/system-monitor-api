import json

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import sys_api.routes.metrics as metrics_routes
from sys_api.main import app


client = TestClient(app)


class FakeRedis:
    def __init__(self):
        self.store = {}
        self.lists = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value):
        self.store[key] = value
        return True

    def incr(self, key):
        value = int(self.store.get(key, 0)) + 1
        self.store[key] = str(value)
        return value

    def lpush(self, key, value):
        self.lists.setdefault(key, [])
        self.lists[key].insert(0, value)
        return len(self.lists[key])

    def lrange(self, key, start, end):
        items = self.lists.get(key, [])

        if end == -1:
            return items[start:]

        return items[start:end + 1]

    def ltrim(self, key, start, end):
        items = self.lists.get(key, [])

        if end == -1:
            self.lists[key] = items[start:]
        else:
            self.lists[key] = items[start:end + 1]

        return True


def fake_get_disk_metrics(min_usage=0, top_n=None):
    data = [
        {
            "filesystem": "/dev/sda1",
            "total": "100G",
            "used": "80G",
            "available": "20G",
            "used_percent": 80,
            "mount_point": "/",
        },
        {
            "filesystem": "/dev/sda2",
            "total": "200G",
            "used": "100G",
            "available": "100G",
            "used_percent": 50,
            "mount_point": "/data",
        },
    ]

    results = [
        item
        for item in data
        if item["used_percent"] >= min_usage
    ]

    results.sort(key=lambda item: item["used_percent"], reverse=True)

    if top_n is not None:
        results = results[:top_n]

    return results


@pytest.fixture(autouse=True)
def mock_dependencies(monkeypatch):
    fake_redis = FakeRedis()

    monkeypatch.setattr(metrics_routes, "redis_client", fake_redis)

    monkeypatch.setattr(
        metrics_routes,
        "get_disk_metrics",
        fake_get_disk_metrics,
    )

    monkeypatch.setattr(
        metrics_routes,
        "get_memory_metrics",
        lambda: {
            "total": "8G",
            "used": "4G",
            "free": "4G",
        },
    )

    monkeypatch.setattr(
        metrics_routes,
        "get_cpu_metrics",
        lambda: {
            "cpu_usage_percent": 12.5,
        },
    )

    monkeypatch.setattr(
        metrics_routes,
        "get_uptime_metrics",
        lambda: {
            "uptime_seconds": 3600,
            "uptime_readable": "0 days, 1 hours, 0 minutes",
        },
    )


def test_root():
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "system monitor api"
    assert data["data"]["status"] == "running"
    assert "timestamp" in data


def test_health():
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "service is healthy"
    assert data["data"]["status"] == "ok"
    assert "timestamp" in data


def test_visits_default_count():
    response = client.get("/visits")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "visit count fetched successfully"
    assert data["data"]["health_visits"] == 0
    assert "timestamp" in data


def test_redis_test():
    response = client.get("/redis-test")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "redis test ok"
    assert data["data"]["service_name"] == "system-monitor-api"


def test_info():
    response = client.get("/info")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "service info"
    assert data["data"]["service_name"] == "system-monitor-api"
    assert data["data"]["version"] == "1.0.0"
    assert "timestamp" in data


def test_disk_success():
    response = client.get("/disk")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "disk info fetched successfully"
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 2
    assert "timestamp" in data


def test_disk_invalid_min_usage_too_high():
    response = client.get("/disk?min_usage=200")
    assert response.status_code == 422


def test_disk_invalid_min_usage_negative():
    response = client.get("/disk?min_usage=-1")
    assert response.status_code == 422


def test_disk_invalid_top_n():
    response = client.get("/disk?top_n=0")
    assert response.status_code == 422


def test_disk_top_n_limit():
    response = client.get("/disk?top_n=1")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 1
    assert data["data"][0]["used_percent"] == 80


def test_disk_min_usage_filter():
    response = client.get("/disk?min_usage=70")
    assert response.status_code == 200

    data = response.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["used_percent"] == 80


def test_disk_item_structure():
    response = client.get("/disk")
    assert response.status_code == 200

    data = response.json()
    item = data["data"][0]

    assert "filesystem" in item
    assert "total" in item
    assert "used" in item
    assert "available" in item
    assert "used_percent" in item
    assert "mount_point" in item


def test_last_disk_no_cache():
    response = client.get("/disk/last")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "no cached disk info found"
    assert data["data"] == {}


def test_disk_history_empty():
    response = client.get("/disk/history")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "disk history fetched successfully"
    assert data["data"]["count"] == 0
    assert data["data"]["items"] == []


def test_disk_last_after_disk_request():
    disk_response = client.get("/disk")
    assert disk_response.status_code == 200

    response = client.get("/disk/last")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "last disk info fetched successfully"
    assert "cached_at" in data["data"]
    assert "cache_age_seconds" in data["data"]
    assert "disk_data" in data["data"]


def test_disk_history_after_disk_request():
    disk_response = client.get("/disk")
    assert disk_response.status_code == 200

    response = client.get("/disk/history")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "disk history fetched successfully"
    assert data["data"]["count"] == 1
    assert len(data["data"]["items"]) == 1


def test_cpu_success():
    response = client.get("/cpu")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "cpu info fetched successfully"
    assert data["data"]["cpu_usage_percent"] == 12.5
    assert "timestamp" in data


def test_memory_success():
    response = client.get("/memory")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "memory info fetched successfully"
    assert data["data"]["total"] == "8G"
    assert data["data"]["used"] == "4G"
    assert data["data"]["free"] == "4G"
    assert "timestamp" in data


def test_uptime_success():
    response = client.get("/uptime")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "uptime info fetched successfully"
    assert data["data"]["uptime_seconds"] == 3600
    assert data["data"]["uptime_readable"] == "0 days, 1 hours, 0 minutes"
    assert "timestamp" in data


def test_metrics_summary_success():
    response = client.get("/metrics/summary")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "metrics summary fetched successfully"
    assert "disk" in data["data"]
    assert "memory" in data["data"]
    assert "cpu" in data["data"]


def test_disk_internal_error(monkeypatch):
    def fake_failure(min_usage, top_n=None):
        raise HTTPException(
            status_code=500,
            detail="mocked disk failure",
        )

    monkeypatch.setattr(metrics_routes, "get_disk_metrics", fake_failure)

    response = client.get("/disk")
    assert response.status_code == 500

    data = response.json()
    assert data["message"] == "request failed"
    assert data["data"] is None
    assert data["error"] == "mocked disk failure"
    assert "timestamp" in data


def test_fake_redis_lrange_behavior():
    fake_redis = FakeRedis()

    fake_redis.lpush("items", json.dumps({"value": 1}))
    fake_redis.lpush("items", json.dumps({"value": 2}))

    result = fake_redis.lrange("items", 0, 0)

    assert len(result) == 1
    assert json.loads(result[0])["value"] == 2

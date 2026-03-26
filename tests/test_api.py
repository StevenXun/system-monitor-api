from fastapi.testclient import TestClient
from sys_api.main import app
import sys_api.routes.metrics as metrics_routes
from fastapi import HTTPException


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "service is healthy"
    assert data["data"]["status"] == "ok"
    assert "timestamp" in data


def test_info():
    response = client.get("/info")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "service info"
    assert data["data"]["service_name"] == "system-monitor-api"
    assert data["data"]["version"] == "1.0.0"
    assert "timestamp" in data


def test_disk_invalid_param():
    response = client.get("/disk?min_usage=200")
    assert response.status_code == 422


def test_disk_success():
    response = client.get("/disk")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "disk info fetched successfully"
    assert "data" in data
    assert "timestamp" in data
    assert isinstance(data["data"], list)


def test_disk_invalid_top_n():
    response = client.get("/disk?top_n=0")
    assert response.status_code == 422


def test_disk_item_structure():
    response = client.get("/disk")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data["data"], list)

    if data["data"]:
        item = data["data"][0]
        assert "filesystem" in item
        assert "total" in item
        assert "used" in item
        assert "available" in item
        assert "used_percent" in item
        assert "mount_point" in item


def test_cpu_success():
    response = client.get("/cpu")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "cpu info fetched successfully"
    assert "data" in data
    assert "timestamp" in data
    assert isinstance(data["data"], dict)
    assert "cpu_usage_percent" in data["data"]


def test_memory_success():
    response = client.get("/memory")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "memory info fetched successfully"
    assert "data" in data
    assert "timestamp" in data
    assert isinstance(data["data"], dict)
    assert "total" in data["data"]
    assert "used" in data["data"]
    assert "free" in data["data"]


def test_uptime_success():
    response = client.get("/uptime")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "uptime info fetched successfully"
    assert "data" in data
    assert "timestamp" in data
    assert isinstance(data["data"], dict)
    assert "uptime_seconds" in data["data"]
    assert "uptime_readable" in data["data"]


def test_disk_top_n_limit():
    response = client.get("/disk?top_n=1")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data["data"], list)
    assert len(data["data"]) <= 1


def test_disk_min_usage_zero():
    response = client.get("/disk?min_usage=0")
    assert response.status_code == 200


def test_disk_min_usage_negative():
    response = client.get("/disk?min_usage=-1")
    assert response.status_code == 422


def test_disk_internal_error(monkeypatch):
    def fake_get_disk_metrics(min_usage, top_n=None):
        raise HTTPException(status_code=500, detail="mocked disk failure")

    monkeypatch.setattr(metrics_routes, "get_disk_metrics", fake_get_disk_metrics)

    response = client.get("/disk")
    assert response.status_code == 500

    data = response.json()
    assert data["message"] == "request failed"
    assert data["data"] is None
    assert data["error"] == "mocked disk failure"
    assert "timestamp" in data

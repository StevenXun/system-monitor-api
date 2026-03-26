from fastapi.testclient import TestClient
from sys_api.main import app

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

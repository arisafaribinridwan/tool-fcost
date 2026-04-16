from __future__ import annotations


def test_index_page_loads(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Excel Automation Tool" in response.data


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}

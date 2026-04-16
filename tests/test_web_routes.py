from __future__ import annotations

from io import BytesIO


def test_index_page_loads(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Excel Automation Tool" in response.data
    assert b"Execute Recipe" in response.data
    assert b"Process Log" in response.data
    assert b"Result" in response.data


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_list_configs_returns_yaml_only(client, app):
    configs_dir = app.config["CONFIGS_DIR"]
    (configs_dir / "recipe-z.yaml").write_text("name: z", encoding="utf-8")
    (configs_dir / "recipe-a.yml").write_text("name: a", encoding="utf-8")
    (configs_dir / "notes.txt").write_text("ignore", encoding="utf-8")

    response = client.get("/api/configs")

    assert response.status_code == 200
    assert response.get_json() == {"configs": ["recipe-a.yml", "recipe-z.yaml"]}


def test_execute_pipeline_requires_valid_extension(client, app):
    configs_dir = app.config["CONFIGS_DIR"]
    (configs_dir / "baseline.yaml").write_text("name: baseline", encoding="utf-8")

    response = client.post(
        "/api/execute",
        data={
            "config_name": "baseline.yaml",
            "source_file": (BytesIO(b"id,name\n1,a"), "sample.txt"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "Ekstensi file tidak didukung" in response.get_json()["error"]


def test_execute_pipeline_dry_run_success(client, app):
    configs_dir = app.config["CONFIGS_DIR"]
    (configs_dir / "baseline.yaml").write_text("name: baseline", encoding="utf-8")

    response = client.post(
        "/api/execute",
        data={
            "config_name": "baseline.yaml",
            "source_file": (BytesIO(b"id,name\n1,a"), "sample.csv"),
        },
        content_type="multipart/form-data",
    )

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["mode"] == "dry-run"
    assert payload["result"]["download_ready"] is False
    assert payload["result"]["download_url"] is None
    assert payload["logs"]

from pathlib import Path

import yaml


def test_dashboard_has_live_oracle_credentials_and_local_only_port():
    lab = yaml.safe_load(Path("lab/docker-compose.yml").read_text())
    demo = yaml.safe_load(Path("dashboard/docker-compose.yml").read_text())
    service = demo["services"]["dashboard"]
    environment = service["environment"]
    runner_env = lab["services"]["runner"]["environment"]
    assert environment["APP_DATABASE_URL"] == runner_env["APP_DATABASE_URL"]
    assert environment["ORACLE_DATABASE_URL"] == runner_env["ORACLE_DATABASE_URL"]
    assert service["ports"] == ["127.0.0.1:8501:8501"]
    assert "lab" in service["networks"]
    assert "demo-ui" in service["networks"]

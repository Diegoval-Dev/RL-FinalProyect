"""F1-T02: no laboratory container can resolve or reach an external host.

Runs on the host because it inspects containers through the docker CLI.
"""

import json
import subprocess
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.lab

COMPOSE_FILE = Path(__file__).parents[2] / "lab" / "docker-compose.yml"
EXTERNAL_HOSTNAME = "example.com"
EXTERNAL_IP = "1.1.1.1"
INTERNAL_HOSTNAME = "db"
CONNECT_TIMEOUT_SECONDS = 3
SERVICES_WITH_SHELL = ("db", "vulnapp")


def compose(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), *args],
        capture_output=True,
        text=True,
    )


def probe(service: str, shell_command: str) -> subprocess.CompletedProcess:
    if service == "runner":
        return compose(
            "run", "--rm", "--no-deps", "-T", "--entrypoint", "bash", service, "-c", shell_command
        )
    return compose("exec", "-T", service, "bash", "-c", shell_command)


def laboratory_services() -> list[str]:
    return [*SERVICES_WITH_SHELL, "runner"]


def test_compose_declares_only_internal_networks():
    config = yaml.safe_load(COMPOSE_FILE.read_text())

    assert config["networks"]
    assert all(network.get("internal") is True for network in config["networks"].values())


def test_compose_publishes_no_ports():
    config = yaml.safe_load(COMPOSE_FILE.read_text())

    assert all("ports" not in service for service in config["services"].values())


def test_running_containers_are_attached_only_to_internal_networks():
    container_ids = compose("ps", "-q").stdout.split()
    assert container_ids

    for container_id in container_ids:
        inspected = subprocess.run(
            ["docker", "inspect", container_id], capture_output=True, text=True
        )
        networks = json.loads(inspected.stdout)[0]["NetworkSettings"]["Networks"]
        for network_name in networks:
            network = json.loads(
                subprocess.run(
                    ["docker", "network", "inspect", network_name], capture_output=True, text=True
                ).stdout
            )[0]
            assert network["Internal"] is True, f"{container_id} on non-internal {network_name}"


@pytest.mark.parametrize("service", laboratory_services())
def test_container_cannot_resolve_external_hostname(service):
    result = probe(service, f"getent hosts {EXTERNAL_HOSTNAME}")

    assert result.returncode != 0


@pytest.mark.parametrize("service", laboratory_services())
def test_container_cannot_connect_to_external_ip(service):
    command = f"timeout {CONNECT_TIMEOUT_SECONDS} bash -c 'exec 3<>/dev/tcp/{EXTERNAL_IP}/443'"
    result = probe(service, command)

    assert result.returncode != 0


@pytest.mark.parametrize("service", laboratory_services())
def test_probe_commands_succeed_against_internal_host(service):
    """Control: the probes above fail because of isolation, not because tools are missing."""
    resolve = probe(service, f"getent hosts {INTERNAL_HOSTNAME}")
    connect = probe(
        service,
        f"timeout {CONNECT_TIMEOUT_SECONDS} bash -c 'exec 3<>/dev/tcp/{INTERNAL_HOSTNAME}/5432'",
    )

    assert resolve.returncode == 0
    assert connect.returncode == 0

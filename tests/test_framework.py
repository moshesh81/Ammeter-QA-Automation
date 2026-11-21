"""Small tests that are easy to run and explain."""

import json
import socket
import time

import pytest

from Ammeters.client import request_current_from_ammeter
from src.testing import test_framework
from src.testing.test_framework import AmmeterTestFramework


def make_config(tmp_path, count=3, duration=1, frequency=10):
    """Create a minimal config used only by a test."""
    config_folder = tmp_path / "config"
    config_folder.mkdir()
    file = config_folder / "config.yaml"
    file.write_text(
        "testing:\n"
        "  sampling:\n"
        f"    measurements_count: {count}\n"
        f"    total_duration_seconds: {duration}\n"
        f"    sampling_frequency_hz: {frequency}\n"
        "ammeters:\n"
        "  greenlee:\n"
        "    port: 5000\n"
        "    command: MEASURE_GREENLEE -get_measurement\n"
        "result_management:\n"
        "  output_dir: results\n",
        encoding="utf-8",
    )
    return file


def test_statistics_and_json_report(tmp_path, monkeypatch):
    config = make_config(tmp_path)
    readings = iter([1.0, 2.0, 3.0])
    monkeypatch.setattr(test_framework, "request_current_from_ammeter",
                        lambda port, command: next(readings))

    report = AmmeterTestFramework(config).run_test("greenlee")

    assert report["status"] == "passed"
    assert report["statistics"]["mean"] == 2.0
    assert report["statistics"]["median"] == 2.0
    assert report["statistics"]["std_dev"] == 1.0
    assert report["statistics"]["minimum"] == 1.0
    assert report["statistics"]["maximum"] == 3.0
    assert len(list((tmp_path / "results").glob("*.json"))) == 1
    saved = json.loads(next((tmp_path / "results").glob("*.json")).read_text())
    assert saved["run_id"] == report["run_id"]
    history = AmmeterTestFramework(config).load_history("greenlee")
    assert len(history) == 1
    assert history[0]["run_id"] == report["run_id"]


def test_invalid_ammeter_type(tmp_path):
    framework = AmmeterTestFramework(make_config(tmp_path))
    with pytest.raises(ValueError, match="Unknown ammeter"):
        framework.run_test("not-a-device")


def test_invalid_sampling_settings(tmp_path):
    config = make_config(tmp_path, count=10, duration=1, frequency=2)
    with pytest.raises(ValueError, match="Cannot fit"):
        AmmeterTestFramework(config)


def test_connection_failure_is_reported(tmp_path, monkeypatch):
    def no_server(port, command):
        raise ConnectionRefusedError("No emulator listening")

    monkeypatch.setattr(test_framework, "request_current_from_ammeter", no_server)
    report = AmmeterTestFramework(make_config(tmp_path, count=2)).run_test("greenlee")

    assert report["status"] == "failed"
    assert report["statistics"]["mean"] is None
    assert len(report["errors"]) == 2


def test_partial_measurements(tmp_path, monkeypatch):
    attempts = iter([1.0, None, 3.0])

    def sometimes_fails(port, command):
        value = next(attempts)
        if value is None:
            raise OSError("Network issue")
        return value

    monkeypatch.setattr(test_framework, "request_current_from_ammeter", sometimes_fails)
    report = AmmeterTestFramework(make_config(tmp_path)).run_test("greenlee")

    assert report["status"] == "partial"
    assert len(report["measurements"]) == 2
    assert len(report["errors"]) == 1
    assert report["statistics"]["mean"] == 2.0


def test_client_returns_float_from_real_socket():
    """Check the actual TCP client without starting an endless emulator."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]

    import threading

    def respond():
        with server:
            connection, _ = server.accept()
            with connection:
                assert connection.recv(1024) == b"MEASURE_TEST"
                connection.sendall(b"12.5")

    thread = threading.Thread(target=respond, daemon=True)
    thread.start()
    assert request_current_from_ammeter(port, b"MEASURE_TEST") == 12.5
    thread.join(timeout=2)


def test_slow_requests_do_not_skip_remaining_samples(tmp_path, monkeypatch):
    """Late requests are recorded, but all measurements are still attempted."""
    def slow_request(port, command):
        time.sleep(0.08)
        return 1.0

    monkeypatch.setattr(test_framework, "request_current_from_ammeter", slow_request)
    config = make_config(tmp_path, count=3, duration=0.04, frequency=100)
    report = AmmeterTestFramework(config).run_test("greenlee")

    assert report["status"] == "passed"
    assert len(report["measurements"]) == 3
    assert report["errors"] == []
    assert len(report["timing_warnings"]) >= 1

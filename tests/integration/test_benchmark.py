import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock


def test_benchmark_uv_not_installed(cli, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    output = cli.execute("benchmark", no_color=True)
    assert "uv is not installed" in output


def test_benchmark_validator_running(cli, monkeypatch):
    from mytonctrl import mytonctrl as mytonctrl_module
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/uv" if name == "uv" else None)
    monkeypatch.setattr(mytonctrl_module, "get_service_status", lambda name: name == "validator")

    output = cli.execute("benchmark", no_color=True)
    assert "validator service is running" in output


def test_benchmark_runs(cli, monkeypatch, tmp_path):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/uv" if name == "uv" else None)
    monkeypatch.setattr(shutil, "copytree", lambda src, dst: None)
    monkeypatch.setattr(shutil, "copy", lambda src, dst: None)

    # mock Path.mkdir and Path.glob used for tl schemes
    monkeypatch.setattr(Path, "mkdir", lambda *a, **kw: None)

    fake_tl = MagicMock()
    fake_tl.__truediv__ = lambda self, other: fake_tl
    fake_tl.glob = lambda pattern: []
    monkeypatch.setattr(Path, "glob", lambda self, pattern: [])

    calls = []

    def fake_subprocess_run(args, **kwargs):
        calls.append({"args": [str(a) for a in args], "kwargs": kwargs})
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(subprocess, "run", fake_subprocess_run)

    cli.execute("benchmark --nodes 4 --tps 1000", no_color=True)

    assert len(calls) == 4

    # uv init
    assert calls[0]["args"] == ["uv", "init", "--no-workspace", "--name", "benchmark"]
    assert "cwd" in calls[0]["kwargs"]
    tmp_dir = str(calls[0]["kwargs"]["cwd"])

    # uv add tontester
    add_args = calls[1]["args"]
    assert add_args[:2] == ["uv", "add"]
    assert "tontester" in add_args[2]

    # uv run generate_tl.py
    assert calls[2]["args"][:2] == ["uv", "run"]
    assert "generate_tl.py" in calls[2]["args"][2]

    # uv run benchmark.py
    run_args = calls[3]["args"]
    assert run_args[:3] == ["uv", "run", "benchmark.py"]
    assert "--build-dir" in run_args
    assert run_args[run_args.index("--build-dir") + 1] == "/usr/bin/ton"
    assert "--source-dir" in run_args
    assert run_args[run_args.index("--source-dir") + 1] == "/usr/src/ton"
    assert "--work-dir" in run_args
    assert run_args[run_args.index("--work-dir") + 1].endswith("/test/integration/.network")
    assert "--nodes" in run_args
    assert "4" in run_args
    assert "--tps" in run_args
    assert "1000" in run_args
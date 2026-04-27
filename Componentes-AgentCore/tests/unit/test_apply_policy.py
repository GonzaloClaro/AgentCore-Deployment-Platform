"""Tests del componente apply_policy.

Verifica lectura de archivos .cedar referenciados desde el manifest
y producción de cedar_policies.json con shape correcta.
"""
import json
import pathlib

import pytest


def write_file(path: pathlib.Path, content: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def test_apply_policy_lee_archivos_y_genera_json(tmp_path, monkeypatch):
    workload = tmp_path / "agents/sandbox/hello"
    workload.mkdir(parents=True)

    write_file(workload / "manifest.yaml", """
apiVersion: v1
kind: Workload
metadata: { name: hello, capability: sandbox, owner: team-x }
spec:
  composition: agent-with-tools
  runtime: { entrypoint: agent.py }
  gateway_policies:
    - gateway: oauth-3lo
      cedar_files: [./policies/p1.cedar, ./policies/p2.cedar]
""")
    write_file(workload / "policies/p1.cedar", "permit(principal, action, resource);")
    write_file(workload / "policies/p2.cedar", "forbid(principal, action, resource);")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WORKLOAD_PATH", str(workload))
    monkeypatch.setenv("MANIFEST_PATH", str(workload / "manifest.yaml"))
    monkeypatch.setenv("OUTPUT_PATH", "cedar_policies.json")
    monkeypatch.setenv("ENVIRONMENT", "dev")

    from apply_policy.apply import main
    rc = main()
    assert rc == 0

    out = json.loads((tmp_path / "cedar_policies.json").read_text())
    assert len(out) == 1
    assert out[0]["gateway"] == "oauth-3lo"
    assert len(out[0]["cedar_policies"]) == 2
    assert "permit" in out[0]["cedar_policies"][0]
    assert "forbid" in out[0]["cedar_policies"][1]


def test_apply_policy_archivo_inexistente_falla(tmp_path, monkeypatch):
    workload = tmp_path / "agents/sandbox/hello"
    workload.mkdir(parents=True)

    write_file(workload / "manifest.yaml", """
apiVersion: v1
kind: Workload
metadata: { name: hello, capability: sandbox, owner: team-x }
spec:
  composition: agent-with-tools
  runtime: { entrypoint: agent.py }
  gateway_policies:
    - gateway: oauth-3lo
      cedar_files: [./policies/no-existe.cedar]
""")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WORKLOAD_PATH", str(workload))
    monkeypatch.setenv("MANIFEST_PATH", str(workload / "manifest.yaml"))
    monkeypatch.setenv("OUTPUT_PATH", "cedar_policies.json")
    monkeypatch.setenv("ENVIRONMENT", "dev")

    from apply_policy.apply import main
    rc = main()
    assert rc == 2, "rc=2 cuando .cedar file no existe"


def test_apply_policy_sin_gateway_policies_genera_json_vacio(tmp_path, monkeypatch):
    workload = tmp_path / "agents/sandbox/hello"
    workload.mkdir(parents=True)

    write_file(workload / "manifest.yaml", """
apiVersion: v1
kind: Workload
metadata: { name: hello, capability: sandbox, owner: team-x }
spec:
  composition: agent-chatbot
  runtime: { entrypoint: agent.py }
""")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WORKLOAD_PATH", str(workload))
    monkeypatch.setenv("MANIFEST_PATH", str(workload / "manifest.yaml"))
    monkeypatch.setenv("OUTPUT_PATH", "cedar_policies.json")
    monkeypatch.setenv("ENVIRONMENT", "dev")

    from apply_policy.apply import main
    rc = main()
    assert rc == 0

    out = json.loads((tmp_path / "cedar_policies.json").read_text())
    assert out == []


def test_apply_policy_multi_gateway(tmp_path, monkeypatch):
    workload = tmp_path / "agents/sandbox/hello"
    workload.mkdir(parents=True)

    write_file(workload / "manifest.yaml", """
apiVersion: v1
kind: Workload
metadata: { name: hello, capability: sandbox, owner: team-x }
spec:
  composition: agent-with-tools
  runtime: { entrypoint: agent.py }
  gateway_policies:
    - gateway: oauth-3lo
      cedar_files: [./policies/web.cedar]
    - gateway: sigv4-m2m
      cedar_files: [./policies/m2m.cedar]
""")
    write_file(workload / "policies/web.cedar", "// web policy")
    write_file(workload / "policies/m2m.cedar", "// m2m policy")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WORKLOAD_PATH", str(workload))
    monkeypatch.setenv("MANIFEST_PATH", str(workload / "manifest.yaml"))
    monkeypatch.setenv("OUTPUT_PATH", "cedar_policies.json")
    monkeypatch.setenv("ENVIRONMENT", "dev")

    from apply_policy.apply import main
    rc = main()
    assert rc == 0

    out = json.loads((tmp_path / "cedar_policies.json").read_text())
    assert len(out) == 2
    gateways = {entry["gateway"] for entry in out}
    assert gateways == {"oauth-3lo", "sigv4-m2m"}

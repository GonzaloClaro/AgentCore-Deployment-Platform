"""Tests del componente validate_structure.

Estos tests son la base para extender con casos por composition.
Ejecutar:  cd Componentes-AgentCore && pytest tests/
"""
import json
import pathlib

import pytest

from validate_structure.validate import validate


def write_manifest(tmp_path: pathlib.Path, content: str) -> pathlib.Path:
    f = tmp_path / "manifest.yaml"
    f.write_text(content)
    return f


def test_valid_chatbot_manifest_pasa(tmp_path, composition_map_path):
    manifest = write_manifest(tmp_path, """
apiVersion: v1
kind: Workload
metadata: { name: hello, capability: sandbox, owner: team-x }
spec:
  composition: agent-chatbot
  runtime: { entrypoint: agent.py }
""")
    result = validate(str(manifest), str(composition_map_path))
    assert result["errors"] == []


def test_composition_inexistente_falla(tmp_path, composition_map_path):
    manifest = write_manifest(tmp_path, """
apiVersion: v1
kind: Workload
metadata: { name: hello, capability: sandbox, owner: team-x }
spec:
  composition: agent-foo-inexistente
  runtime: { entrypoint: agent.py }
""")
    result = validate(str(manifest), str(composition_map_path))
    assert any("agent-foo-inexistente" in e for e in result["errors"])


def test_agent_with_kb_sin_knowledge_base_falla(tmp_path, composition_map_path):
    manifest = write_manifest(tmp_path, """
apiVersion: v1
kind: Workload
metadata: { name: hello, capability: sandbox, owner: team-x }
spec:
  composition: agent-with-kb
  runtime: { entrypoint: agent.py }
""")
    result = validate(str(manifest), str(composition_map_path))
    assert any("knowledge_base" in e for e in result["errors"])


def test_cedar_file_inexistente_falla(tmp_path, composition_map_path):
    manifest = write_manifest(tmp_path, """
apiVersion: v1
kind: Workload
metadata: { name: hello, capability: sandbox, owner: team-x }
spec:
  composition: agent-chatbot
  runtime: { entrypoint: agent.py }
  gateway_policies:
    - gateway: oauth-3lo
      cedar_files: [./policies/no-existe.cedar]
""")
    result = validate(str(manifest), str(composition_map_path))
    assert any("no existe" in e and "no-existe.cedar" in e for e in result["errors"])


def test_inline_policy_json_invalido_falla(tmp_path, composition_map_path):
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{not valid json")
    manifest = write_manifest(tmp_path, """
apiVersion: v1
kind: Workload
metadata: { name: hello, capability: sandbox, owner: team-x }
spec:
  composition: agent-chatbot
  runtime: { entrypoint: agent.py }
  runtime_iam:
    inline_policies:
      - { name: bad, file: ./bad.json }
""")
    result = validate(str(manifest), str(composition_map_path))
    assert any("JSON inválido" in e for e in result["errors"])


def test_tool_lambda_sin_handler_falla(tmp_path, composition_map_path):
    manifest = write_manifest(tmp_path, """
apiVersion: v1
kind: Workload
metadata: { name: hello, capability: sandbox, owner: team-x }
spec:
  composition: agent-chatbot
  runtime: { entrypoint: agent.py }
  tool: { kind: lambda }
""")
    result = validate(str(manifest), str(composition_map_path))
    assert any("handler" in e for e in result["errors"])


def test_gateway_no_default_warning_no_error(tmp_path, composition_map_path):
    manifest = write_manifest(tmp_path, """
apiVersion: v1
kind: Workload
metadata: { name: hello, capability: sandbox, owner: team-x }
spec:
  composition: agent-chatbot
  runtime: { entrypoint: agent.py }
  gateway_targets:
    - gateway: my-custom-gw
""")
    result = validate(str(manifest), str(composition_map_path))
    assert result["errors"] == []
    assert any("my-custom-gw" in w for w in result["warnings"])

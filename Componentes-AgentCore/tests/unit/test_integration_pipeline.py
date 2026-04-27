"""Test de integración: simulación del pipeline secuencial.

Encadena los componentes que deben funcionar juntos:
  validate_structure → apply_policy → render_tfvars

Este test pega los componentes para detectar regresiones en el contrato entre ellos.
"""
import json
import pathlib

import pytest


def write_file(path: pathlib.Path, content: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def test_pipeline_completo_workload_chatbot_con_policies(tmp_path, monkeypatch, composition_map_path):
    """Simulación: workload chatbot + Cedar policies + IAM inline policy.

    Pasos:
      1. validate_structure → debe pasar (errors=0)
      2. apply_policy        → genera cedar_policies.json
      3. render_tfvars       → produce tfvars con shape correcto
    """
    workload = tmp_path / "agents/sandbox/full"
    workload.mkdir(parents=True)

    # Manifest con todo
    write_file(workload / "manifest.yaml", """
apiVersion: v1
kind: Workload
metadata:
  name: full-chatbot
  capability: sandbox
  owner: team-platform
  tags: [test]
spec:
  composition: agent-chatbot
  runtime: { entrypoint: agent.py }
  gateway_policies:
    - gateway: oauth-3lo
      attach_mode: ENFORCE
      cedar_files: [./policies/all-permit.cedar]
  runtime_iam:
    managed_policy_arns: ["arn:aws:iam::111122223333:policy/managed-x"]
    inline_policies:
      - { name: read-bucket, file: ./iam/read.json }
""")
    write_file(workload / "policies/all-permit.cedar", "permit(principal, action, resource);")
    write_file(workload / "iam/read.json", json.dumps({
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Action": "s3:GetObject", "Resource": "*"}]
    }))

    monkeypatch.chdir(tmp_path)

    # ─── Paso 1: validate_structure ───
    from validate_structure.validate import validate
    result = validate(str(workload / "manifest.yaml"), str(composition_map_path))
    assert result["errors"] == [], f"validate_structure errores: {result['errors']}"

    # ─── Paso 2: apply_policy ───
    monkeypatch.setenv("WORKLOAD_PATH", str(workload))
    monkeypatch.setenv("MANIFEST_PATH", str(workload / "manifest.yaml"))
    monkeypatch.setenv("OUTPUT_PATH", "cedar_policies.json")
    monkeypatch.setenv("ENVIRONMENT", "dev")

    from apply_policy.apply import main as apply_main
    assert apply_main() == 0

    cedar = json.loads((tmp_path / "cedar_policies.json").read_text())
    assert len(cedar) == 1
    assert cedar[0]["gateway"] == "oauth-3lo"

    # ─── Paso 3: render_tfvars ───
    write_file(tmp_path / "image_meta.json", '{"image_uri": "ecr.test/full:abc"}')
    write_file(tmp_path / "artifact_meta.json", '{"s3_uri": "s3://test/full.zip"}')
    write_file(tmp_path / "env-defaults.yaml", """
environment: dev
default_role_arn: "arn:aws:iam::111122223333:role/agentcore-runtime"
""")

    monkeypatch.setenv("ENV_DEFAULTS_PATH", "env-defaults.yaml")

    from render_tfvars.render import main as render_main
    assert render_main() == 0

    tfvars = json.loads((tmp_path / "terraform.auto.tfvars.json").read_text())
    composition = (tmp_path / "composition_name.txt").read_text().strip()

    # Verificaciones del contrato cross-component:
    assert composition == "agent-chatbot"
    assert tfvars["image_uri"] == "ecr.test/full:abc"

    # gateway_policies debe haber sido enriquecido por render_tfvars con attach_mode del manifest
    assert len(tfvars["gateway_policies"]) == 1
    assert tfvars["gateway_policies"][0]["attach_mode"] == "ENFORCE"
    assert tfvars["gateway_policies"][0]["cedar_policies"] == ["permit(principal, action, resource);"]

    # runtime_iam: managed + inline (con policy_document como string)
    assert tfvars["runtime_iam"]["managed_policy_arns"] == [
        "arn:aws:iam::111122223333:policy/managed-x"
    ]
    inline = tfvars["runtime_iam"]["inline_policies"]
    assert len(inline) == 1
    assert inline[0]["name"] == "read-bucket"
    assert isinstance(inline[0]["policy_document"], str)
    parsed = json.loads(inline[0]["policy_document"])
    assert parsed["Statement"][0]["Action"] == "s3:GetObject"


def test_pipeline_falla_si_apply_policy_falla(tmp_path, monkeypatch, composition_map_path):
    """Si apply_policy falla por archivo missing, el pipeline NO debería intentar render."""
    workload = tmp_path / "agents/sandbox/broken"
    workload.mkdir(parents=True)

    write_file(workload / "manifest.yaml", """
apiVersion: v1
kind: Workload
metadata: { name: broken, capability: sandbox, owner: team-x }
spec:
  composition: agent-with-tools
  runtime: { entrypoint: agent.py }
  gateway_policies:
    - gateway: oauth-3lo
      cedar_files: [./policies/missing.cedar]
""")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WORKLOAD_PATH", str(workload))
    monkeypatch.setenv("MANIFEST_PATH", str(workload / "manifest.yaml"))
    monkeypatch.setenv("OUTPUT_PATH", "cedar_policies.json")
    monkeypatch.setenv("ENVIRONMENT", "dev")

    from apply_policy.apply import main as apply_main
    rc = apply_main()
    assert rc == 2  # falla limpio

    # cedar_policies.json no debería existir (o estar vacío). render_tfvars NO debería correr.

"""Tests del componente render_tfvars.

Verifica que dado un manifest + env-defaults + outputs intermedios,
el tfvars JSON producido tenga la shape esperada para cada composition.
"""
import json
import os
import pathlib

import pytest


def write_file(path: pathlib.Path, content: str) -> pathlib.Path:
    path.write_text(content)
    return path


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    """Setup workdir con manifest + env-defaults + meta files."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def run_render(workdir, monkeypatch, manifest_yaml, env_defaults_yaml="environment: dev\naws_region: us-east-1\n"):
    """Ejecuta render_tfvars.render.main() con env vars seteadas."""
    write_file(workdir / "manifest.yaml", manifest_yaml)
    write_file(workdir / "env-defaults.yaml", env_defaults_yaml)
    write_file(workdir / "image_meta.json", '{"image_uri": "ecr.test/img:abc"}')
    write_file(workdir / "artifact_meta.json", '{"s3_uri": "s3://test/x.zip"}')

    monkeypatch.setenv("MANIFEST_PATH", "manifest.yaml")
    monkeypatch.setenv("ENV_DEFAULTS_PATH", "env-defaults.yaml")
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("WORKLOAD_PATH", ".")

    from render_tfvars.render import main
    rc = main()
    assert rc == 0, "render_tfvars debe terminar con rc=0"

    return json.loads((workdir / "terraform.auto.tfvars.json").read_text()), \
           (workdir / "composition_name.txt").read_text().strip()


def test_render_chatbot_minimo(workdir, monkeypatch):
    tfvars, composition = run_render(workdir, monkeypatch, """
apiVersion: v1
kind: Workload
metadata: { name: hello, capability: sandbox, owner: team-x }
spec:
  composition: agent-chatbot
  runtime: { entrypoint: agent.py, env: { LOG_LEVEL: INFO } }
""")

    assert composition == "agent-chatbot"
    assert tfvars["name"] == "hello"
    assert tfvars["capability"] == "sandbox"
    assert tfvars["image_uri"] == "ecr.test/img:abc"
    assert tfvars["artifact_s3_uri"] == "s3://test/x.zip"
    assert tfvars["runtime"]["entrypoint"] == "agent.py"
    # runtime_iam vacío por default
    assert tfvars["runtime_iam"]["managed_policy_arns"] == []
    assert tfvars["runtime_iam"]["inline_policies"] == []


def test_render_con_runtime_iam_managed(workdir, monkeypatch):
    tfvars, _ = run_render(workdir, monkeypatch, """
apiVersion: v1
kind: Workload
metadata: { name: x, capability: y, owner: z }
spec:
  composition: agent-chatbot
  runtime: { entrypoint: agent.py }
  runtime_iam:
    managed_policy_arns:
      - "arn:aws:iam::111122223333:policy/agentcore-shared-read-kb"
""")

    assert tfvars["runtime_iam"]["managed_policy_arns"] == [
        "arn:aws:iam::111122223333:policy/agentcore-shared-read-kb"
    ]
    assert tfvars["runtime_iam"]["inline_policies"] == []


def test_render_con_inline_policy_resuelve_archivo(workdir, monkeypatch):
    write_file(workdir / "iam_test.json", json.dumps({
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Action": "s3:GetObject", "Resource": "*"}]
    }))

    tfvars, _ = run_render(workdir, monkeypatch, """
apiVersion: v1
kind: Workload
metadata: { name: x, capability: y, owner: z }
spec:
  composition: agent-chatbot
  runtime: { entrypoint: agent.py }
  runtime_iam:
    inline_policies:
      - { name: read-bucket, file: ./iam_test.json }
""")

    inline = tfvars["runtime_iam"]["inline_policies"]
    assert len(inline) == 1
    assert inline[0]["name"] == "read-bucket"
    # policy_document debe ser string JSON serializado (no dict)
    assert isinstance(inline[0]["policy_document"], str)
    parsed = json.loads(inline[0]["policy_document"])
    assert parsed["Statement"][0]["Action"] == "s3:GetObject"


def test_render_inline_policy_inexistente_falla(workdir, monkeypatch):
    write_file(workdir / "manifest.yaml", """
apiVersion: v1
kind: Workload
metadata: { name: x, capability: y, owner: z }
spec:
  composition: agent-chatbot
  runtime: { entrypoint: agent.py }
  runtime_iam:
    inline_policies:
      - { name: ghost, file: ./no-existe.json }
""")
    write_file(workdir / "env-defaults.yaml", "environment: dev\n")
    write_file(workdir / "image_meta.json", "{}")
    write_file(workdir / "artifact_meta.json", "{}")

    monkeypatch.setenv("MANIFEST_PATH", "manifest.yaml")
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("WORKLOAD_PATH", ".")

    from render_tfvars.render import main
    rc = main()
    assert rc == 2, "rc=2 cuando inline policy file no existe"


def test_render_gateway_policies_merge_attach_mode(workdir, monkeypatch):
    """gateway_policies debe combinar attach_mode del manifest con cedar_policies de cedar_policies.json."""
    write_file(workdir / "cedar_policies.json", json.dumps([
        {"gateway": "oauth-3lo", "cedar_policies": ["permit(...);"]}
    ]))

    tfvars, _ = run_render(workdir, monkeypatch, """
apiVersion: v1
kind: Workload
metadata: { name: x, capability: y, owner: z }
spec:
  composition: agent-with-tools
  runtime: { entrypoint: agent.py }
  gateway_policies:
    - gateway: oauth-3lo
      attach_mode: ENFORCE
      cedar_files: [./policies/x.cedar]
""")

    gp = tfvars["gateway_policies"]
    assert len(gp) == 1
    assert gp[0]["gateway"] == "oauth-3lo"
    assert gp[0]["attach_mode"] == "ENFORCE"
    assert gp[0]["cedar_policies"] == ["permit(...);"]


def test_render_env_defaults_se_propagan(workdir, monkeypatch):
    tfvars, _ = run_render(workdir, monkeypatch, """
apiVersion: v1
kind: Workload
metadata: { name: x, capability: y, owner: z }
spec:
  composition: agent-base
  runtime: { entrypoint: agent.py }
""", env_defaults_yaml="""
environment: dev
aws_region: us-west-2
vpc_id: vpc-abc
subnet_ids: [subnet-1, subnet-2]
kms_key_arn: arn:aws:kms:us-west-2:123:alias/test
default_role_arn: arn:aws:iam::123:role/agentcore-runtime
permissions_boundary_arn: arn:aws:iam::123:policy/CorpBoundary
""")

    assert tfvars["vpc_id"] == "vpc-abc"
    assert tfvars["subnet_ids"] == ["subnet-1", "subnet-2"]
    assert tfvars["kms_key_arn"] == "arn:aws:kms:us-west-2:123:alias/test"
    assert tfvars["default_role_arn"] == "arn:aws:iam::123:role/agentcore-runtime"
    assert tfvars["permissions_boundary_arn"] == "arn:aws:iam::123:policy/CorpBoundary"

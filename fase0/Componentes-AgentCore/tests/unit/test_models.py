"""Tests del manejo de spec.models[] — validate_structure + render_tfvars."""
import json
import pathlib

import pytest


def write_file(path: pathlib.Path, content: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


# ───── validate_structure: chequeos contra whitelist ─────

def test_model_bedrock_permitido_pasa(tmp_path, composition_map_path, allowed_models_path):
    manifest = write_file(tmp_path / "manifest.yaml", """
apiVersion: v1
kind: Workload
metadata: { name: x, capability: y, owner: z }
spec:
  composition: agent-chatbot
  runtime: { entrypoint: agent.py }
  models:
    - alias: PRIMARY_MODEL
      provider: bedrock
      bedrock: { model_id: "anthropic.claude-3-5-sonnet-20241022-v2:0" }
""")
    from validate_structure.validate import validate
    result = validate(str(manifest), str(composition_map_path), str(allowed_models_path), "dev")
    assert result["errors"] == []


def test_model_bedrock_no_permitido_falla(tmp_path, composition_map_path, allowed_models_path):
    manifest = write_file(tmp_path / "manifest.yaml", """
apiVersion: v1
kind: Workload
metadata: { name: x, capability: y, owner: z }
spec:
  composition: agent-chatbot
  runtime: { entrypoint: agent.py }
  models:
    - alias: PRIMARY_MODEL
      provider: bedrock
      bedrock: { model_id: "ai21.jamba-1-5-large-v1:0" }
""")
    from validate_structure.validate import validate
    result = validate(str(manifest), str(composition_map_path), str(allowed_models_path), "dev")
    assert any("ai21.jamba" in e and "NO está en allowed_models" in e for e in result["errors"])


def test_model_opus_en_prd_falla(tmp_path, composition_map_path, allowed_models_path):
    manifest = write_file(tmp_path / "manifest.yaml", """
apiVersion: v1
kind: Workload
metadata: { name: x, capability: y, owner: z }
spec:
  composition: agent-chatbot
  runtime: { entrypoint: agent.py }
  models:
    - alias: PRIMARY_MODEL
      provider: bedrock
      bedrock: { model_id: "anthropic.claude-3-opus-20240229-v1:0" }
""")
    from validate_structure.validate import validate
    # En dev sí pasa
    assert validate(str(manifest), str(composition_map_path), str(allowed_models_path), "dev")["errors"] == []
    # En prd NO pasa (no está en environments del whitelist)
    result_prd = validate(str(manifest), str(composition_map_path), str(allowed_models_path), "prd")
    assert any("no permitido en 'prd'" in e for e in result_prd["errors"])


def test_alias_duplicado_falla(tmp_path, composition_map_path, allowed_models_path):
    manifest = write_file(tmp_path / "manifest.yaml", """
apiVersion: v1
kind: Workload
metadata: { name: x, capability: y, owner: z }
spec:
  composition: agent-chatbot
  runtime: { entrypoint: agent.py }
  models:
    - alias: PRIMARY_MODEL
      provider: bedrock
      bedrock: { model_id: "anthropic.claude-3-5-sonnet-20241022-v2:0" }
    - alias: PRIMARY_MODEL
      provider: bedrock
      bedrock: { model_id: "anthropic.claude-3-5-haiku-20241022-v1:0" }
""")
    from validate_structure.validate import validate
    result = validate(str(manifest), str(composition_map_path), str(allowed_models_path), "dev")
    assert any("duplicado" in e for e in result["errors"])


def test_bedrock_sin_model_id_ni_inference_profile_falla(tmp_path, composition_map_path, allowed_models_path):
    manifest = write_file(tmp_path / "manifest.yaml", """
apiVersion: v1
kind: Workload
metadata: { name: x, capability: y, owner: z }
spec:
  composition: agent-chatbot
  runtime: { entrypoint: agent.py }
  models:
    - alias: BAD_MODEL
      provider: bedrock
      bedrock: {}
""")
    from validate_structure.validate import validate
    result = validate(str(manifest), str(composition_map_path), str(allowed_models_path), "dev")
    assert any("model_id O inference_profile_arn" in e for e in result["errors"])


def test_azure_sin_endpoint_falla(tmp_path, composition_map_path, allowed_models_path):
    manifest = write_file(tmp_path / "manifest.yaml", """
apiVersion: v1
kind: Workload
metadata: { name: x, capability: y, owner: z }
spec:
  composition: agent-chatbot
  runtime: { entrypoint: agent.py }
  models:
    - alias: AZURE_MODEL
      provider: azure
      azure:
        deployment: gpt-4o-prod
        api_version: "2024-08-01-preview"
        api_key_secret_var: AZURE_KEY
""")
    from validate_structure.validate import validate
    result = validate(str(manifest), str(composition_map_path), str(allowed_models_path), "dev")
    assert any("azure requiere endpoint" in e for e in result["errors"])


# ───── render_tfvars: producir models[] con shape correcta ─────

def test_render_models_bedrock(tmp_path, monkeypatch):
    write_file(tmp_path / "manifest.yaml", """
apiVersion: v1
kind: Workload
metadata: { name: x, capability: y, owner: z }
spec:
  composition: agent-chatbot
  runtime: { entrypoint: agent.py }
  models:
    - alias: PRIMARY_MODEL
      provider: bedrock
      bedrock:
        model_id: "anthropic.claude-3-5-sonnet-20241022-v2:0"
        region: us-west-2
""")
    write_file(tmp_path / "env-defaults.yaml", "environment: dev\naws_region: us-east-1\naccount_id: 111122223333\n")
    write_file(tmp_path / "image_meta.json", "{}")
    write_file(tmp_path / "artifact_meta.json", "{}")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MANIFEST_PATH", "manifest.yaml")
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("WORKLOAD_PATH", ".")

    from render_tfvars.render import main
    assert main() == 0

    tfvars = json.loads((tmp_path / "terraform.auto.tfvars.json").read_text())
    models = tfvars["models"]
    assert len(models) == 1
    assert models[0]["alias"] == "PRIMARY_MODEL"
    assert models[0]["provider"] == "bedrock"
    assert models[0]["model_id"] == "anthropic.claude-3-5-sonnet-20241022-v2:0"
    assert models[0]["region"] == "us-west-2"   # override del manifest sobre el default
    assert models[0]["api_key_secret_arn"] == ""  # bedrock no tiene


def test_render_models_azure_resuelve_secret_arn(tmp_path, monkeypatch):
    write_file(tmp_path / "manifest.yaml", """
apiVersion: v1
kind: Workload
metadata: { name: x, capability: y, owner: z }
spec:
  composition: agent-chatbot
  runtime: { entrypoint: agent.py }
  models:
    - alias: AZURE_MODEL
      provider: azure
      azure:
        endpoint: "https://my-org.openai.azure.com/"
        deployment: "gpt-4o-prod"
        model_id: gpt-4o
        api_version: "2024-08-01-preview"
        api_key_secret_var: AZURE_OPENAI_API_KEY
""")
    write_file(tmp_path / "env-defaults.yaml", "environment: dev\naws_region: us-east-1\naccount_id: 111122223333\n")
    write_file(tmp_path / "image_meta.json", "{}")
    write_file(tmp_path / "artifact_meta.json", "{}")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MANIFEST_PATH", "manifest.yaml")
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("WORKLOAD_PATH", ".")

    from render_tfvars.render import main
    assert main() == 0

    tfvars = json.loads((tmp_path / "terraform.auto.tfvars.json").read_text())
    models = tfvars["models"]
    assert len(models) == 1
    m = models[0]
    assert m["provider"] == "azure"
    assert m["endpoint"] == "https://my-org.openai.azure.com/"
    assert m["deployment"] == "gpt-4o-prod"
    # ARN del secret resuelto convencionalmente: agentcore/dev/azure/azure_model
    assert m["api_key_secret_arn"] == \
        "arn:aws:secretsmanager:us-east-1:111122223333:secret:agentcore/dev/azure/azure_model"


def test_render_sin_models_devuelve_lista_vacia(tmp_path, monkeypatch):
    write_file(tmp_path / "manifest.yaml", """
apiVersion: v1
kind: Workload
metadata: { name: x, capability: y, owner: z }
spec:
  composition: agent-chatbot
  runtime: { entrypoint: agent.py }
""")
    write_file(tmp_path / "env-defaults.yaml", "environment: dev\n")
    write_file(tmp_path / "image_meta.json", "{}")
    write_file(tmp_path / "artifact_meta.json", "{}")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MANIFEST_PATH", "manifest.yaml")
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("WORKLOAD_PATH", ".")

    from render_tfvars.render import main
    assert main() == 0

    tfvars = json.loads((tmp_path / "terraform.auto.tfvars.json").read_text())
    assert tfvars["models"] == []

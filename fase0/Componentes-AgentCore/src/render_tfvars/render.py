"""render_tfvars (fase 0): combina manifest + env-defaults + artifact_meta → tfvars JSON.

Versión simplificada respecto al render_tfvars global:
- NO procesa image_meta (no hay container build en fase 0)
- NO procesa cedar_policies (sin gateway policies)
- NO procesa runtime_iam.inline_policies (modo zip simple)
- NO procesa gateway_targets (sin tools en fase 0)
- SÍ proyecta artifact_meta.s3_bucket / s3_key como code_s3_bucket / code_s3_prefix
  (lo que esperan los modules runtime/code_configuration)
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from utils.manifest_parser import load_manifest


def main() -> int:
    manifest_path = os.environ["MANIFEST_PATH"]
    env_defaults_path = os.environ.get("ENV_DEFAULTS_PATH", "env-defaults.yaml")
    artifact_meta_path = os.environ.get("ARTIFACT_META_PATH", "artifact_meta.json")
    output_tfvars = os.environ.get("OUTPUT_TFVARS", "terraform.auto.tfvars.json")
    output_composition = os.environ.get("OUTPUT_COMPOSITION", "composition_name.txt")
    env = os.environ["ENVIRONMENT"]

    manifest = load_manifest(manifest_path)
    metadata = manifest["metadata"]
    spec = manifest["spec"]
    composition = spec["composition"]

    if composition not in ("agent-base-zip", "agent-with-kb-zip"):
        print(f"ERROR: composition '{composition}' no soportada en fase 0", file=sys.stderr)
        print("       válidas: agent-base-zip, agent-with-kb-zip", file=sys.stderr)
        return 2

    env_defaults = {}
    if pathlib.Path(env_defaults_path).exists():
        with open(env_defaults_path) as f:
            env_defaults = yaml.safe_load(f) or {}

    artifact_meta = {}
    if pathlib.Path(artifact_meta_path).exists():
        artifact_meta = json.loads(pathlib.Path(artifact_meta_path).read_text())

    if not artifact_meta.get("s3_bucket") or not artifact_meta.get("s3_key"):
        print("ERROR: artifact_meta.json incompleto (falta s3_bucket o s3_key)", file=sys.stderr)
        print(f"       contenido: {artifact_meta}", file=sys.stderr)
        return 2

    # ──────────────────────────────────────────────────────────────────
    # Models — declarados en spec.models[], producen env vars al runtime
    # ──────────────────────────────────────────────────────────────────
    models_spec = spec.get("models", []) or []
    models_resolved = []
    aws_region_default = env_defaults.get("aws_region", "us-east-1")
    account_id = env_defaults.get("account_id", "")

    for m in models_spec:
        alias = m["alias"]
        provider = m["provider"]
        block = m.get(provider, {}) or {}

        if provider == "bedrock":
            models_resolved.append({
                "alias": alias,
                "provider": "bedrock",
                "model_id": block.get("model_id", ""),
                "region": block.get("region", aws_region_default),
                "inference_profile_arn": block.get("inference_profile_arn", ""),
                "endpoint": "",
                "deployment": "",
                "api_version": "",
                "api_key_secret_arn": "",
            })
        elif provider == "azure":
            secret_name = f"agentcore/{env}/azure/{alias.lower()}"
            secret_arn = (
                f"arn:aws:secretsmanager:{aws_region_default}:{account_id}:secret:{secret_name}"
                if account_id else ""
            )
            models_resolved.append({
                "alias": alias,
                "provider": "azure",
                "model_id": block.get("model_id", ""),
                "region": aws_region_default,
                "inference_profile_arn": "",
                "endpoint": block.get("endpoint", ""),
                "deployment": block.get("deployment", ""),
                "api_version": block.get("api_version", ""),
                "api_key_secret_arn": secret_arn,
            })

    if models_resolved:
        print(f"[render_tfvars] {len(models_resolved)} modelo(s): {[m['alias'] for m in models_resolved]}")

    # ──────────────────────────────────────────────────────────────────
    # Construir tfvars con shape de las composiciones de fase 0
    # ──────────────────────────────────────────────────────────────────
    tfvars = {
        "name": metadata["name"],
        "capability": metadata["capability"],
        "owner": metadata.get("owner", ""),
        "environment": env,
        "tags": metadata.get("tags", []),

        # Modo zip: ubicación del artifact en S3
        "code_s3_bucket": artifact_meta["s3_bucket"],
        "code_s3_prefix": artifact_meta["s3_key"],

        "pipeline_id": os.environ.get("CI_PIPELINE_ID", "manual"),

        "kms_key_arn": env_defaults.get("kms_key_arn", ""),
        "default_role_arn": env_defaults.get("default_role_arn", ""),
        "vpc_id": env_defaults.get("vpc_id", ""),
        "subnet_ids": env_defaults.get("subnet_ids", []),
        "permissions_boundary_arn": env_defaults.get("permissions_boundary_arn"),

        "runtime": spec.get("runtime", {}),
        "observability": spec.get("observability", {"enabled": True}),
        "features": spec.get("features", {"enable_observability": True}),
        "models": models_resolved,

        "runtime_iam": {
            "managed_policy_arns": [],
            "inline_policies": [],
            "attach_bedrock_invoke": True,
        },
    }

    # Campos solo de agent-with-kb-zip
    if composition == "agent-with-kb-zip":
        tfvars["memory"] = spec.get("memory", {"strategy": "summarization"})
        tfvars["knowledge_base"] = spec.get("knowledge_base", {})
        tfvars["prompts"] = spec.get("prompts", [])

    pathlib.Path(output_tfvars).write_text(json.dumps(tfvars, indent=2))
    pathlib.Path(output_composition).write_text(composition + "\n")
    print(f"[render_tfvars] composition={composition}")
    print(f"[render_tfvars] {output_tfvars} escrito ({len(json.dumps(tfvars))} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

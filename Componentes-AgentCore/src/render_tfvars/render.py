"""render_tfvars: combina manifest + env-defaults + outputs intermedios → tfvars JSON."""
from __future__ import annotations

import json
import os
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from utils.manifest_parser import load_manifest


def merge_dicts(base: dict, overlay: dict) -> dict:
    out = dict(base)
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge_dicts(out[k], v)
        else:
            out[k] = v
    return out


def main() -> int:
    manifest_path = os.environ["MANIFEST_PATH"]
    env_defaults_path = os.environ.get("ENV_DEFAULTS_PATH", "env-defaults.yaml")
    artifact_meta_path = os.environ.get("ARTIFACT_META_PATH", "artifact_meta.json")
    image_meta_path = os.environ.get("IMAGE_META_PATH", "image_meta.json")
    output_tfvars = os.environ.get("OUTPUT_TFVARS", "terraform.auto.tfvars.json")
    output_composition = os.environ.get("OUTPUT_COMPOSITION", "composition_name.txt")
    env = os.environ["ENVIRONMENT"]

    manifest = load_manifest(manifest_path)
    env_defaults = {}
    if pathlib.Path(env_defaults_path).exists():
        with open(env_defaults_path) as f:
            env_defaults = yaml.safe_load(f) or {}

    artifact_meta = {}
    if pathlib.Path(artifact_meta_path).exists():
        artifact_meta = json.loads(pathlib.Path(artifact_meta_path).read_text())

    image_meta = {}
    if pathlib.Path(image_meta_path).exists():
        image_meta = json.loads(pathlib.Path(image_meta_path).read_text())

    # Cedar policies inyectadas por el componente apply_policy (si existe).
    # Cada entry tiene {"gateway": ..., "cedar_policies": [contenido strings]}
    # Hacemos merge con el manifest para recuperar attach_mode.
    cedar_policies_path = os.environ.get("CEDAR_POLICIES_PATH", "cedar_policies.json")
    cedar_resolved = []
    if pathlib.Path(cedar_policies_path).exists():
        cedar_resolved = json.loads(pathlib.Path(cedar_policies_path).read_text())

    # Mezclar attach_mode del manifest con el contenido resuelto
    manifest_gw_policies = {p["gateway"]: p for p in load_manifest(manifest_path).get("spec", {}).get("gateway_policies", [])}
    gateway_policies = []
    for entry in cedar_resolved:
        gw = entry["gateway"]
        attach_mode = manifest_gw_policies.get(gw, {}).get("attach_mode", "LOGONLY")
        gateway_policies.append({
            "gateway": gw,
            "attach_mode": attach_mode,
            "cedar_policies": entry["cedar_policies"],
        })

    # runtime_iam: leer archivos JSON declarados en inline_policies[].file
    workload_path_var = os.environ.get("WORKLOAD_PATH", ".")
    runtime_iam_spec = load_manifest(manifest_path).get("spec", {}).get("runtime_iam", {})
    inline_resolved = []
    for entry in runtime_iam_spec.get("inline_policies", []) or []:
        file_path = pathlib.Path(workload_path_var) / entry["file"]
        if not file_path.exists():
            print(f"ERROR: inline policy file no encontrado: {file_path}", file=sys.stderr)
            return 2
        # Validar que sea JSON válido y serializar como string (formato esperado por aws_iam_role_policy.policy)
        policy_doc = json.loads(file_path.read_text())
        inline_resolved.append({
            "name": entry["name"],
            "policy_document": json.dumps(policy_doc),
        })
        print(f"[render_tfvars] inline policy {entry['name']} ← {entry['file']} ({len(policy_doc.get('Statement', []))} statements)")

    runtime_iam = {
        "managed_policy_arns": runtime_iam_spec.get("managed_policy_arns", []) or [],
        "inline_policies": inline_resolved,
        "attach_bedrock_invoke": runtime_iam_spec.get("attach_bedrock_invoke", True),
    }

    # ──────────────────────────────────────────────────────────────────────
    # Models — declarados en spec.models[], producen env vars al runtime.
    # Para Azure: api_key viene de Secrets Manager (resuelto por upload_secret).
    # ──────────────────────────────────────────────────────────────────────
    models_spec = load_manifest(manifest_path).get("spec", {}).get("models", []) or []
    models_resolved = []
    aws_region_default = env_defaults.get("aws_region", "us-east-1")

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
                # Campos azure vacíos para shape uniforme
                "endpoint": "",
                "deployment": "",
                "api_version": "",
                "api_key_secret_arn": "",
            })
        elif provider == "azure":
            # Convención: secret_name = "agentcore/{env}/azure/{alias_lower}"
            # upload_secret YA subió la API key a Secrets Manager con ese nombre.
            secret_name = f"agentcore/{env}/azure/{alias.lower()}"
            account_id = env_defaults.get("account_id", "")
            region_default = aws_region_default
            secret_arn = (
                f"arn:aws:secretsmanager:{region_default}:{account_id}:secret:{secret_name}"
                if account_id else ""
            )
            models_resolved.append({
                "alias": alias,
                "provider": "azure",
                "model_id": block.get("model_id", ""),
                "region": region_default,
                "inference_profile_arn": "",
                "endpoint": block.get("endpoint", ""),
                "deployment": block.get("deployment", ""),
                "api_version": block.get("api_version", ""),
                "api_key_secret_arn": secret_arn,
            })
        else:
            print(f"[render_tfvars] WARN: provider desconocido '{provider}' en alias {alias}", file=sys.stderr)

    if models_resolved:
        print(f"[render_tfvars] {len(models_resolved)} modelo(s): {[m['alias'] for m in models_resolved]}")

    composition = manifest["spec"]["composition"]
    metadata = manifest["metadata"]
    spec = manifest["spec"]

    tfvars = {
        "name": metadata["name"],
        "capability": metadata["capability"],
        "owner": metadata.get("owner", ""),
        "environment": env,
        "tags": metadata.get("tags", []),
        # vienen de outputs intermedios
        "image_uri": image_meta.get("image_uri", ""),
        "artifact_s3_uri": artifact_meta.get("s3_uri", ""),
        # vienen del env-defaults del proyecto agentcore-{env}
        "vpc_id": env_defaults.get("vpc_id", ""),
        "subnet_ids": env_defaults.get("subnet_ids", []),
        "kms_key_arn": env_defaults.get("kms_key_arn", ""),
        "default_role_arn": env_defaults.get("default_role_arn", ""),
        # spec del workload (composition decide qué consume)
        "runtime": spec.get("runtime", {}),
        "memory": {"strategy": spec.get("runtime", {}).get("memory_strategy", "summarization")},
        "knowledge_base": spec.get("knowledge_base", {}),
        "prompts": spec.get("prompts", []),
        "gateway_targets": spec.get("gateway_targets", []),
        "observability": spec.get("observability", {"enabled": True}),
        "features": spec.get("features", {}),
        # gateway_policies vienen de apply_policy (cedar_policies.json), no del manifest directamente
        "gateway_policies": gateway_policies,
        # runtime_iam: managed ARNs + inline JSONs resueltos a strings
        "runtime_iam": runtime_iam,
        "permissions_boundary_arn": env_defaults.get("permissions_boundary_arn"),
        # models: lista de modelos resueltos con shape uniforme (bedrock + azure)
        "models": models_resolved,
    }

    pathlib.Path(output_tfvars).write_text(json.dumps(tfvars, indent=2))
    pathlib.Path(output_composition).write_text(composition + "\n")
    print(f"[render_tfvars] composition={composition}")
    print(f"[render_tfvars] {output_tfvars} escrito ({len(json.dumps(tfvars))} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

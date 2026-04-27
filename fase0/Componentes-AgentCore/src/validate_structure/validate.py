"""validate_structure (fase 0): validación cruzada del workload contra la plataforma.

Checks de fase 0 (subset del global):
  1. La `composition` declarada es una de las dos válidas (agent-base-zip | agent-with-kb-zip).
  2. El entrypoint declarado en spec.runtime.entrypoint existe en src/.
  3. Si declara `prompts`, los archivos referenciados existen.
  4. Si composition es agent-with-kb-zip, valida presencia de knowledge_base config.
  5. Validación de naming patterns (kebab-case en metadata.name y capability).
  6. Cada modelo en spec.models[] está en allowed_models.yml para el ambiente target (si existe).

NO valida (fase 0 no usa estos):
  - gateway_targets / gateway_policies (sin gateways custom)
  - runtime_iam.inline_policies (sin custom IAM en fase 0)
  - tool.kind (sin tool-lambda en fase 0)
  - oauth_provider (sin MCP server en fase 0)

Output: validation_report.json con count_errors, count_warnings, items[].
Sale 1 si count_errors > 0, 0 si solo warnings o todo OK.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from utils.manifest_parser import load_manifest


SUPPORTED_COMPOSITIONS = {"agent-base-zip", "agent-with-kb-zip"}
DEFAULT_ALLOWED_MODELS_PATH = "config_files/allowed_models.yml"


def load_allowed_models(path: str) -> dict:
    p = pathlib.Path(path)
    if not p.exists():
        return {}
    raw = yaml.safe_load(p.read_text()) or {}
    out = {}
    for provider, entries in raw.items():
        if not isinstance(entries, list):
            continue
        out[provider] = {e["id"]: e for e in entries if "id" in e}
    return out


def validate_composition(spec: dict, errors: list) -> None:
    composition = spec.get("composition", "")
    if composition not in SUPPORTED_COMPOSITIONS:
        errors.append(
            f"composition '{composition}' no soportada en fase 0. "
            f"Válidas: {sorted(SUPPORTED_COMPOSITIONS)}"
        )


def validate_entrypoint(workload_path: pathlib.Path, spec: dict, errors: list) -> None:
    entrypoint = spec.get("runtime", {}).get("entrypoint", "")
    if not entrypoint:
        errors.append("spec.runtime.entrypoint no declarado")
        return

    candidate = workload_path / "src" / entrypoint
    if not candidate.exists():
        errors.append(f"entrypoint '{entrypoint}' no existe en src/ (esperado: {candidate})")


def validate_prompts(workload_path: pathlib.Path, spec: dict, errors: list) -> None:
    prompts = spec.get("prompts", []) or []
    for idx, p in enumerate(prompts):
        file_path = workload_path / p.get("file", "")
        if not file_path.exists():
            errors.append(f"prompts[{idx}]: archivo '{p.get('file')}' no existe")


def validate_kb_requirements(spec: dict, errors: list, warnings: list) -> None:
    if spec.get("composition") != "agent-with-kb-zip":
        return
    kb = spec.get("knowledge_base", {})
    if not kb:
        warnings.append(
            "composition agent-with-kb-zip sin knowledge_base declarado. "
            "El módulo se va a saltar la creación de KB."
        )
    if not kb.get("sources_file") and kb:
        warnings.append("knowledge_base sin sources_file — la KB se crea sin data sources iniciales")


def validate_naming(metadata: dict, errors: list) -> None:
    import re
    pattern = re.compile(r"^[a-z][a-z0-9-]{2,40}$")
    for field in ("name", "capability"):
        value = metadata.get(field, "")
        if not pattern.match(value):
            errors.append(f"metadata.{field} '{value}' debe cumplir kebab-case [a-z0-9-]{{3,41}}")


def validate_models(spec: dict, environment: str, allowed: dict, errors: list, warnings: list) -> None:
    models = spec.get("models", []) or []
    seen_aliases = set()

    for idx, m in enumerate(models):
        alias = m.get("alias", f"<unnamed-{idx}>")
        provider = m.get("provider", "")

        if alias in seen_aliases:
            errors.append(f"models[{idx}]: alias '{alias}' está duplicado")
        seen_aliases.add(alias)

        if not allowed:
            warnings.append(f"models[{idx}]: allowed_models.yml no encontrado, skip whitelist check")
            continue

        provider_allowed = allowed.get(provider, {})
        block = m.get(provider, {})
        model_id = block.get("model_id", "")

        if not model_id:
            warnings.append(f"models[{idx}]: model_id no declarado (alias={alias})")
            continue

        entry = provider_allowed.get(model_id)
        if not entry:
            errors.append(
                f"models[{idx}]: model_id '{model_id}' (provider={provider}) no está en allowed_models.yml"
            )
            continue

        envs = entry.get("environments", [])
        if envs and environment not in envs:
            errors.append(
                f"models[{idx}]: model '{model_id}' no permitido en {environment} "
                f"(allowed: {envs})"
            )


def main() -> int:
    manifest_path = os.environ["MANIFEST_PATH"]
    workload_path = pathlib.Path(os.environ.get("WORKLOAD_PATH", "."))
    environment = os.environ.get("ENVIRONMENT", "dev")
    allowed_models_path = os.environ.get("ALLOWED_MODELS_PATH", DEFAULT_ALLOWED_MODELS_PATH)
    output_path = os.environ.get("OUTPUT_REPORT", "validation_report.json")

    manifest = load_manifest(manifest_path)
    metadata = manifest.get("metadata", {})
    spec = manifest.get("spec", {})
    allowed = load_allowed_models(allowed_models_path)

    errors: list = []
    warnings: list = []

    validate_composition(spec, errors)
    validate_naming(metadata, errors)
    validate_entrypoint(workload_path, spec, errors)
    validate_prompts(workload_path, spec, errors)
    validate_kb_requirements(spec, errors, warnings)
    validate_models(spec, environment, allowed, errors, warnings)

    report = {
        "manifest": manifest_path,
        "environment": environment,
        "count_errors": len(errors),
        "count_warnings": len(warnings),
        "items": [{"severity": "error", "message": e} for e in errors]
                 + [{"severity": "warning", "message": w} for w in warnings],
    }
    pathlib.Path(output_path).write_text(json.dumps(report, indent=2))

    print(f"[validate_structure] errors={len(errors)} warnings={len(warnings)}")
    for e in errors:
        print(f"  ✗ {e}")
    for w in warnings:
        print(f"  ⚠ {w}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

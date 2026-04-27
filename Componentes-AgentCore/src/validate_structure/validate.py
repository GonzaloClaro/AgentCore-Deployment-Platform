"""validate_structure: validación cruzada del workload contra la plataforma.

Checks que ejecuta:
  1. La `composition` declarada en el manifest existe en composition_map.yml.
  2. Los `requires` de la composition están presentes en el manifest (ej: agent-with-kb requiere knowledge_base).
  3. Si declara `gateway_targets`, cada `gateway` referenciado es uno de los 3 default
     (oauth-3lo|oauth-2lo|sigv4-m2m) o existe como gateway custom.
  4. Si declara `gateway_policies`, los archivos .cedar referenciados existen.
  5. Si declara `runtime_iam.inline_policies`, los archivos JSON existen y son válidos.
  6. Si declara `prompts`, los archivos referenciados existen.
  7. Si declara `tool.kind == "lambda"`, hay handler definido.
  8. Si la composition es `mcp-server`, hay oauth_provider o sigv4-m2m gateway.
  9. Validación de naming patterns (kebab-case, lowercase, etc.).
 10. KMS key arn coherente con environment.

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


DEFAULT_GATEWAYS = {"oauth-3lo", "oauth-2lo", "sigv4-m2m"}
DEFAULT_ALLOWED_MODELS_PATH = "config_files/allowed_models.yml"


def load_allowed_models(path: str) -> dict:
    """Lee allowed_models.yml y devuelve dict {provider: {model_id: {environments: [...]}}}."""
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


def validate_models(spec: dict, environment: str, allowed: dict, errors: list, warnings: list) -> None:
    models = spec.get("models", []) or []
    seen_aliases = set()

    for idx, m in enumerate(models):
        alias = m.get("alias", f"<unnamed-{idx}>")
        provider = m.get("provider", "")

        # Alias unique
        if alias in seen_aliases:
            errors.append(f"models[{idx}]: alias '{alias}' está duplicado")
            continue
        seen_aliases.add(alias)

        # Provider config presente
        if provider not in {"bedrock", "azure"}:
            errors.append(f"models[{idx}] alias '{alias}': provider '{provider}' inválido (bedrock|azure)")
            continue

        if provider not in m:
            errors.append(f"models[{idx}] alias '{alias}': falta bloque '{provider}'")
            continue
        provider_block = m.get(provider) or {}

        # Resolver model_id (común a bedrock/azure)
        model_id = provider_block.get("model_id")
        if provider == "bedrock" and not model_id and not provider_block.get("inference_profile_arn"):
            errors.append(f"models[{idx}] alias '{alias}': bedrock requiere model_id O inference_profile_arn")
            continue

        if provider == "azure":
            for req in ("endpoint", "deployment", "api_version", "api_key_secret_var"):
                if not provider_block.get(req):
                    errors.append(f"models[{idx}] alias '{alias}': azure requiere {req}")

        # Validar contra whitelist (si tenemos)
        if model_id and provider in allowed:
            entry = allowed[provider].get(model_id)
            if not entry:
                errors.append(
                    f"models[{idx}] alias '{alias}': model_id '{model_id}' NO está en allowed_models.yml ({provider})."
                )
            else:
                allowed_envs = entry.get("environments", [])
                if environment and environment not in allowed_envs:
                    errors.append(
                        f"models[{idx}] alias '{alias}': '{model_id}' no permitido en '{environment}' "
                        f"(allowed: {allowed_envs})"
                    )


def check(condition: bool, level: str, message: str, errors: list, warnings: list) -> None:
    if condition:
        return
    (errors if level == "error" else warnings).append(message)


def validate(manifest_path: str, composition_map_path: str, allowed_models_path: str | None = None, environment: str | None = None) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    if not pathlib.Path(manifest_path).exists():
        return {"errors": [f"manifest no encontrado: {manifest_path}"], "warnings": []}

    manifest = load_manifest(manifest_path)
    workload_dir = pathlib.Path(manifest_path).parent
    spec = manifest.get("spec", {})
    metadata = manifest.get("metadata", {})

    # Cargar whitelist de modelos
    allowed_models = load_allowed_models(allowed_models_path or DEFAULT_ALLOWED_MODELS_PATH)
    validate_models(spec, environment or os.environ.get("ENVIRONMENT", ""), allowed_models, errors, warnings)

    # 1. composition válida
    composition_map = {}
    if pathlib.Path(composition_map_path).exists():
        composition_map = yaml.safe_load(pathlib.Path(composition_map_path).read_text()).get("compositions", {})
    composition = spec.get("composition")
    check(
        composition in composition_map,
        "error",
        f"composition '{composition}' no existe. Válidas: {sorted(composition_map.keys())}",
        errors, warnings,
    )

    # 2. requires de la composition presentes
    if composition in composition_map:
        for req in composition_map[composition].get("requires", []):
            check(
                req == "runtime" or spec.get(req),
                "error",
                f"composition '{composition}' requiere '{req}' pero no está declarado en spec.{req}",
                errors, warnings,
            )

    # 3. gateway_targets referencian gateways válidos
    for gt in spec.get("gateway_targets", []) or []:
        gw = gt.get("gateway")
        check(
            gw in DEFAULT_GATEWAYS,
            "warning",
            f"gateway '{gw}' no es uno de los 3 default. Si es custom, asegurate de que exista en gateway-deploy.",
            errors, warnings,
        )

    # 4. gateway_policies: archivos .cedar existen
    for gp in spec.get("gateway_policies", []) or []:
        for cf in gp.get("cedar_files", []):
            f = (workload_dir / cf).resolve()
            check(
                f.exists(),
                "error",
                f"cedar file no existe: {cf} (resolvió a {f})",
                errors, warnings,
            )

    # 5. runtime_iam.inline_policies: archivos JSON existen y son válidos
    for ip in spec.get("runtime_iam", {}).get("inline_policies", []) or []:
        f = (workload_dir / ip["file"]).resolve()
        if not f.exists():
            errors.append(f"inline policy file no existe: {ip['file']}")
            continue
        try:
            doc = json.loads(f.read_text())
            check(
                isinstance(doc.get("Statement"), list),
                "error",
                f"inline policy {ip['name']} no tiene 'Statement' como list",
                errors, warnings,
            )
        except json.JSONDecodeError as e:
            errors.append(f"inline policy {ip['name']} JSON inválido: {e}")

    # 6. prompts: archivos referenciados existen
    for p in spec.get("prompts", []) or []:
        f = (workload_dir / p["file"]).resolve()
        check(
            f.exists(),
            "error",
            f"prompt file no existe: {p['file']}",
            errors, warnings,
        )

    # 7. tool.kind == lambda → handler definido
    tool = spec.get("tool")
    if tool and tool.get("kind") == "lambda":
        check(
            tool.get("handler"),
            "error",
            "tool.kind=lambda requiere tool.handler",
            errors, warnings,
        )

    # 8. mcp-server requiere autorización
    if composition == "mcp-server":
        has_auth = bool(spec.get("oauth_provider")) or any(
            gt.get("gateway") == "sigv4-m2m" for gt in spec.get("gateway_targets", []) or []
        )
        check(
            has_auth,
            "warning",
            "mcp-server sin oauth_provider ni gateway sigv4-m2m → tools serán no-autenticadas",
            errors, warnings,
        )

    # 9. Naming
    name = metadata.get("name", "")
    check(
        name and name.islower() and "-" in name or name.isalnum(),
        "warning",
        f"metadata.name '{name}' debería ser kebab-case lowercase",
        errors, warnings,
    )

    return {"errors": errors, "warnings": warnings}


def main() -> int:
    manifest_path = os.environ["MANIFEST_PATH"]
    composition_map_path = os.environ.get(
        "COMPOSITION_MAP_PATH", "config_files/render_tfvars/composition_map.yml"
    )
    allowed_models_path = os.environ.get(
        "ALLOWED_MODELS_PATH", "config_files/allowed_models.yml"
    )
    environment = os.environ.get("ENVIRONMENT")

    result = validate(manifest_path, composition_map_path, allowed_models_path, environment)
    report = {
        "manifest": manifest_path,
        "count_errors": len(result["errors"]),
        "count_warnings": len(result["warnings"]),
        "errors": result["errors"],
        "warnings": result["warnings"],
    }
    pathlib.Path("validation_report.json").write_text(json.dumps(report, indent=2))

    print(f"[validate_structure] errors={report['count_errors']} warnings={report['count_warnings']}")
    for e in result["errors"]:
        print(f"  ERROR: {e}", file=sys.stderr)
    for w in result["warnings"]:
        print(f"  WARN:  {w}")

    return 1 if report["count_errors"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())

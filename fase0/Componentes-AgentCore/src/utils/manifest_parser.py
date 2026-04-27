"""Lectura y validación de manifest.yaml del workload."""
from __future__ import annotations

import json
import pathlib
import yaml
from jsonschema import Draft202012Validator


def load_manifest(path: str | pathlib.Path) -> dict:
    p = pathlib.Path(path)
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_manifest(manifest: dict, schema_path: str | pathlib.Path) -> list[str]:
    """Devuelve lista de errores; vacío = manifest válido."""
    with pathlib.Path(schema_path).open("r", encoding="utf-8") as f:
        schema = json.load(f)
    validator = Draft202012Validator(schema)
    errors = []
    for err in validator.iter_errors(manifest):
        path = ".".join(str(p) for p in err.absolute_path) or "<root>"
        errors.append(f"{path}: {err.message}")
    return errors


def workload_kind(manifest: dict) -> str:
    """Infiere kind (agents|mcp|tools) del manifest. Si no está explícito, mira la composition."""
    composition = manifest.get("spec", {}).get("composition", "")
    if composition.startswith("mcp-"):
        return "mcp"
    return manifest.get("metadata", {}).get("kind", "agents")

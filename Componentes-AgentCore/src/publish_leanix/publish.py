"""publish_leanix: extrae metadata de manifests y publica fact sheets a LeanIX."""
from __future__ import annotations

import glob
import json
import os
import pathlib
import sys

import requests
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from utils.manifest_parser import load_manifest


def manifest_to_factsheet(manifest: dict) -> dict:
    md = manifest.get("metadata", {})
    sp = manifest.get("spec", {})
    return {
        "type": "Application",
        "name": md.get("name"),
        "displayName": md.get("name"),
        "description": md.get("description", ""),
        "tags": md.get("tags", []),
        "fields": {
            "capability": md.get("capability"),
            "owner": md.get("owner"),
            "composition": sp.get("composition"),
            "has_kb": "knowledge_base" in sp,
            "gateway_targets": [g.get("gateway") for g in sp.get("gateway_targets", [])],
        },
    }


def main() -> int:
    manifests_glob = os.environ["MANIFESTS_GLOB"]
    endpoint = os.environ["LEANIX_ENDPOINT"]
    token_var = os.environ.get("LEANIX_TOKEN_VAR", "LEANIX_API_TOKEN")
    token = os.environ.get(token_var)
    if not token:
        print(f"ERROR: {token_var} no está definido", file=sys.stderr)
        return 2

    files = glob.glob(manifests_glob, recursive=True)
    print(f"[publish_leanix] {len(files)} manifests encontrados")

    report = {"published": [], "errors": []}
    for f in files:
        manifest = load_manifest(f)
        factsheet = manifest_to_factsheet(manifest)
        try:
            resp = requests.post(
                f"{endpoint}/factsheets/upsert",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=factsheet, timeout=30,
            )
            resp.raise_for_status()
            report["published"].append({"manifest": f, "id": resp.json().get("id")})
        except Exception as e:
            report["errors"].append({"manifest": f, "error": str(e)})

    pathlib.Path("leanix_publish_report.json").write_text(json.dumps(report, indent=2))
    print(f"[publish_leanix] publicados={len(report['published'])} errores={len(report['errors'])}")
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

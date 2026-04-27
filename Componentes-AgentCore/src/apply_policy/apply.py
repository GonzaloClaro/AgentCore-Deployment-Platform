"""apply_policy: lee archivos .cedar referenciados en el manifest y los empaqueta como JSON
para que render_tfvars los inyecte en gateway_policies[] del tfvars.

Manifest expected:
  spec:
    gateway_policies:
      - gateway: oauth-3lo
        cedar_files: [./policies/insurance.cedar, ./policies/audit.cedar]
      - gateway: sigv4-m2m
        cedar_files: [./policies/m2m.cedar]

Output (cedar_policies.json):
  [
    {"gateway": "oauth-3lo", "cedar_policies": ["...contenido cedar 1...", "...contenido cedar 2..."]},
    {"gateway": "sigv4-m2m", "cedar_policies": ["...contenido cedar..."]}
  ]
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from utils.manifest_parser import load_manifest


def main() -> int:
    workload_path = pathlib.Path(os.environ["WORKLOAD_PATH"])
    manifest_path = os.environ["MANIFEST_PATH"]
    output_path = os.environ.get("OUTPUT_PATH", "cedar_policies.json")

    manifest = load_manifest(manifest_path)
    policies_spec = manifest.get("spec", {}).get("gateway_policies", [])

    if not policies_spec:
        print("[apply_policy] no hay gateway_policies en el manifest, skip")
        pathlib.Path(output_path).write_text("[]")
        return 0

    out = []
    for entry in policies_spec:
        gateway = entry["gateway"]
        cedar_files = entry.get("cedar_files", [])
        contents = []
        for cf in cedar_files:
            cf_path = (workload_path / cf).resolve()
            if not cf_path.exists():
                print(f"ERROR: cedar file no encontrado: {cf_path}", file=sys.stderr)
                return 2
            content = cf_path.read_text(encoding="utf-8")
            print(f"[apply_policy] {gateway} ← {cf} ({len(content)} bytes)")
            contents.append(content)
        out.append({"gateway": gateway, "cedar_policies": contents})

    pathlib.Path(output_path).write_text(json.dumps(out, indent=2))
    print(f"[apply_policy] {len(out)} entry(ies) escritas en {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

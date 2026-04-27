"""validate_manifest: valida manifest.yaml contra JSON-schema."""
from __future__ import annotations

import os
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from utils.manifest_parser import load_manifest, validate_manifest


def main() -> int:
    manifest_path = os.environ["MANIFEST_PATH"]
    schema_version = os.environ.get("SCHEMA_VERSION", "v1")
    schema_path = pathlib.Path("config_files/validate_manifest/manifest.schema.json")

    print(f"[validate_manifest] manifest={manifest_path} schema_version={schema_version}")
    if not pathlib.Path(manifest_path).exists():
        print(f"ERROR: manifest no encontrado: {manifest_path}", file=sys.stderr)
        return 2

    manifest = load_manifest(manifest_path)
    errors = validate_manifest(manifest, schema_path)
    if errors:
        print(f"[validate_manifest] manifest inválido: {len(errors)} error(es)")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"[validate_manifest] OK: {manifest['metadata']['name']} ({manifest['spec']['composition']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

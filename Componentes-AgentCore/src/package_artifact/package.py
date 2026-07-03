"""package_artifact: zipea el workload y sube a S3 como artefacto auditable."""
from __future__ import annotations

import json
import os
import pathlib
import sys
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from utils.aws_client import client
from utils.manifest_parser import load_manifest


def make_zip(workload_path: pathlib.Path, output_zip: pathlib.Path) -> None:
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in workload_path.rglob("*"):
            if f.is_file() and not any(part.startswith(".") for part in f.parts):
                zf.write(f, f.relative_to(workload_path))


def main() -> int:
    workload_path = pathlib.Path(os.environ["WORKLOAD_PATH"])
    capability = os.environ["CAPABILITY"]
    name = os.environ["WORKLOAD_NAME"]
    kind = os.environ.get("KIND", "agents")
    env = os.environ["ENVIRONMENT"]
    bucket = os.environ["S3_BUCKET"]
    sha = os.environ.get("CI_COMMIT_SHORT_SHA", "local")

    if not workload_path.is_dir():
        print(f"ERROR: workload_path no existe: {workload_path}", file=sys.stderr)
        return 2

    manifest = load_manifest(workload_path / "manifest.yaml")
    enable_audit = manifest.get("spec", {}).get("features", {}).get("enable_artifact_audit", True)
    if not enable_audit:
        print("[package_artifact] enable_artifact_audit=false — se salta zip/upload")
        pathlib.Path("artifact_meta.json").write_text(json.dumps({
            "kind": kind, "capability": capability, "name": name,
            "environment": env, "sha": sha, "s3_uri": "", "audit_skipped": True,
        }, indent=2))
        return 0

    output_zip = pathlib.Path(f"/tmp/{name}-{sha}.zip")
    make_zip(workload_path, output_zip)
    print(f"[package_artifact] zip creado: {output_zip} ({output_zip.stat().st_size} bytes)")

    s3_key = f"{kind}/{capability}/{name}/{sha}.zip"
    s3_key_latest = f"{kind}/{capability}/{name}/latest.zip"
    s3 = client("s3")
    s3.upload_file(str(output_zip), bucket, s3_key)
    s3.upload_file(str(output_zip), bucket, s3_key_latest)
    s3_uri = f"s3://{bucket}/{s3_key}"
    print(f"[package_artifact] subido a {s3_uri}")

    meta = {
        "kind": kind,
        "capability": capability,
        "name": name,
        "environment": env,
        "sha": sha,
        "s3_bucket": bucket,
        "s3_key": s3_key,
        "s3_uri": s3_uri,
        "size_bytes": output_zip.stat().st_size,
    }
    pathlib.Path("artifact_meta.json").write_text(json.dumps(meta, indent=2))
    print("[package_artifact] artifact_meta.json escrito")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

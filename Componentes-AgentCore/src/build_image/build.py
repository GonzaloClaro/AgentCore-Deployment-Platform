"""build_image: construye imagen ARM64 y la sube a ECR."""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from utils.aws_client import client, account_id, DEFAULT_REGION


def run(cmd: list[str]) -> None:
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def ecr_login(region: str) -> None:
    pwd = subprocess.check_output(
        ["aws", "ecr", "get-login-password", "--region", region]
    ).decode().strip()
    acct = account_id()
    registry = f"{acct}.dkr.ecr.{region}.amazonaws.com"
    p = subprocess.run(
        ["docker", "login", "--username", "AWS", "--password-stdin", registry],
        input=pwd, text=True, check=True,
    )
    return registry


def main() -> int:
    workload_path = pathlib.Path(os.environ["WORKLOAD_PATH"])
    ecr_repo = os.environ["ECR_REPO"]
    image_tag = os.environ.get("IMAGE_TAG") or os.environ.get("CI_COMMIT_SHORT_SHA", "latest")
    dockerfile = os.environ.get("DOCKERFILE_PATH", "config_files/build_image/agent-runtime.Dockerfile")
    platform = os.environ.get("BUILD_PLATFORM", "linux/arm64")
    region = os.environ.get("AWS_REGION", DEFAULT_REGION)

    workload_dockerfile = workload_path / "src" / "Dockerfile"
    if workload_dockerfile.exists():
        print(f"[build_image] override: usando Dockerfile del workload {workload_dockerfile}")
        dockerfile = str(workload_dockerfile)

    registry = ecr_login(region)
    image_uri = f"{registry}/{ecr_repo}:{image_tag}"

    run(["docker", "buildx", "create", "--use", "--name", "agentcore-builder"])
    run([
        "docker", "buildx", "build",
        "--platform", platform,
        "-f", dockerfile,
        "-t", image_uri,
        "--push",
        str(workload_path / "src"),
    ])

    print(f"[build_image] imagen publicada: {image_uri}")
    pathlib.Path("image_meta.json").write_text(json.dumps({
        "image_uri": image_uri,
        "platform": platform,
        "ecr_repo": ecr_repo,
        "tag": image_tag,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

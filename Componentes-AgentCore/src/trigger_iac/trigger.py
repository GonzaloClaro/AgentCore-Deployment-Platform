"""trigger_iac: dispara el pipeline downstream del deployable agentcore-{env}."""
from __future__ import annotations

import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from utils.gitlab_client import trigger_pipeline


def main() -> int:
    target_project = os.environ["TARGET_PROJECT"]
    target_ref = os.environ.get("TARGET_REF", "main")
    infra_ref = os.environ.get("INFRA_REF", "main")
    tfvars_artifact = os.environ.get("TFVARS_ARTIFACT", "terraform.auto.tfvars.json")
    composition_artifact = os.environ.get("COMPOSITION_ARTIFACT", "composition_name.txt")
    env = os.environ["ENVIRONMENT"]

    composition = pathlib.Path(composition_artifact).read_text().strip()
    tfvars_content = pathlib.Path(tfvars_artifact).read_text()

    print(f"[trigger_iac] target={target_project}@{target_ref} composition={composition}")
    resp = trigger_pipeline(
        target_project=target_project,
        ref=target_ref,
        variables={
            "UPSTREAM_PIPELINE_ID": os.environ.get("CI_PIPELINE_ID", ""),
            "UPSTREAM_PROJECT": os.environ.get("CI_PROJECT_PATH", ""),
            "TFVARS_JSON": tfvars_content,
            "COMPOSITION_NAME": composition,
            "INFRA_REF": infra_ref,
            "ENVIRONMENT": env,
        },
    )
    print(f"[trigger_iac] pipeline downstream creado: {resp.get('web_url')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

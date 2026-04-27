"""publish_prompt: publica/versiona prompts en Bedrock Prompt Management."""
from __future__ import annotations

import json
import os
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from utils.aws_client import client


def upsert_prompt(bedrock, name: str, body: dict) -> str:
    """Crea o actualiza un prompt y devuelve ARN versionado."""
    description = body.get("description", "")
    variants = body.get("variants", [])
    default_variant = body.get("default_variant") or (variants[0]["name"] if variants else "default")

    try:
        existing = bedrock.list_prompts(maxResults=100)
        match = next((p for p in existing.get("promptSummaries", []) if p["name"] == name), None)
    except Exception:
        match = None

    if match is None:
        resp = bedrock.create_prompt(
            name=name,
            description=description,
            variants=variants,
            defaultVariant=default_variant,
        )
        prompt_id = resp["id"]
    else:
        prompt_id = match["id"]
        bedrock.update_prompt(
            promptIdentifier=prompt_id,
            name=name,
            description=description,
            variants=variants,
            defaultVariant=default_variant,
        )

    version = bedrock.create_prompt_version(promptIdentifier=prompt_id)
    return version["arn"]


def main() -> int:
    prompts_dir = pathlib.Path(os.environ["PROMPTS_DIR"])
    workload = os.environ["WORKLOAD_NAME"]
    capability = os.environ["CAPABILITY"]
    env = os.environ["ENVIRONMENT"]

    if not prompts_dir.is_dir():
        print(f"[publish_prompt] no hay prompts en {prompts_dir}, skip")
        pathlib.Path("prompt_arns.json").write_text("{}")
        return 0

    bedrock = client("bedrock-agent")
    arns = {}
    for f in sorted(prompts_dir.glob("*.yaml")):
        body = yaml.safe_load(f.read_text())
        name = f"{env}-{capability}-{workload}-{f.stem}"
        arn = upsert_prompt(bedrock, name, body)
        alias = body.get("alias", f.stem.upper() + "_PROMPT_ARN")
        arns[alias] = arn
        print(f"[publish_prompt] {name} -> {arn} (alias env={alias})")

    pathlib.Path("prompt_arns.json").write_text(json.dumps(arns, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

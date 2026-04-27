"""Cliente mínimo para disparar pipelines multi-project en GitLab."""
from __future__ import annotations

import os
import urllib.parse
import requests


def trigger_pipeline(target_project: str, ref: str, variables: dict) -> dict:
    """Dispara un pipeline en otro proyecto via API trigger token o pipeline token.

    Usa CI_JOB_TOKEN cuando es disponible (multi-project trigger).
    """
    token = os.environ["CI_JOB_TOKEN"]
    server = os.environ["CI_SERVER_HOST"]
    encoded = urllib.parse.quote(target_project, safe="")
    url = f"https://{server}/api/v4/projects/{encoded}/trigger/pipeline"
    payload = {"token": token, "ref": ref}
    for k, v in variables.items():
        payload[f"variables[{k}]"] = v
    resp = requests.post(url, data=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()

"""drift_check: analiza un plan.json de Terraform para detectar drift y categorizar severidad.

Severidad de cambios:
  - critical: destroy/replace de runtime, gateway, knowledge_base
  - high:     update de runtime alias, IAM role, policies
  - medium:   update de tags, env_vars
  - low:      drift de read-only attributes

Si la severidad detectada >= SEVERITY_THRESHOLD, publica alerta a SNS_TOPIC_ARN.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from utils.aws_client import client


SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}

CRITICAL_RESOURCES = {
    "aws_bedrockagentcore_agent_runtime",
    "aws_bedrockagentcore_gateway",
    "aws_bedrockagent_knowledge_base",
    "aws_s3vectors_vector_bucket",
}

HIGH_RESOURCES = {
    "aws_bedrockagentcore_agent_runtime_alias",
    "aws_iam_role",
    "aws_iam_role_policy",
    "aws_iam_role_policy_attachment",
    "aws_bedrockagentcore_oauth2_credential_provider",
    "aws_bedrockagentcore_memory",
    "aws_secretsmanager_secret",
}


def severity_of_change(change: dict) -> str:
    actions = change.get("change", {}).get("actions", [])
    resource_type = change.get("type", "")

    if "delete" in actions or actions == ["delete", "create"]:
        if resource_type in CRITICAL_RESOURCES:
            return "critical"
        if resource_type in HIGH_RESOURCES:
            return "high"
        return "medium"

    if "update" in actions:
        if resource_type in CRITICAL_RESOURCES:
            return "high"
        if resource_type in HIGH_RESOURCES:
            return "medium"
        return "low"

    if "create" in actions:
        # Algo nuevo en la cuenta que TF declara → no es drift, es deploy normal
        return "low"

    return "low"


def analyze_plan(plan_json_path: str) -> dict:
    if not pathlib.Path(plan_json_path).exists():
        return {"drift": False, "reason": "no plan.json", "items": []}

    plan = json.loads(pathlib.Path(plan_json_path).read_text())
    changes = plan.get("resource_changes", [])

    drifts = []
    max_severity = "low"
    for ch in changes:
        actions = ch.get("change", {}).get("actions", [])
        if actions == ["no-op"] or actions == ["read"]:
            continue
        sev = severity_of_change(ch)
        drifts.append({
            "address": ch.get("address"),
            "type": ch.get("type"),
            "actions": actions,
            "severity": sev,
        })
        if SEVERITY_RANK[sev] > SEVERITY_RANK[max_severity]:
            max_severity = sev

    return {
        "drift": len(drifts) > 0,
        "max_severity": max_severity,
        "count": len(drifts),
        "items": drifts[:50],   # cap para no inundar
    }


def alert_sns(topic_arn: str, env: str, report: dict) -> None:
    sns = client("sns")
    items_summary = "\n".join(
        f"  - [{it['severity']}] {it['address']}: {','.join(it['actions'])}"
        for it in report["items"][:10]
    )
    msg = (
        f"AgentCore drift detected in {env}\n"
        f"max severity: {report['max_severity']}\n"
        f"count: {report['count']}\n\n"
        f"top items:\n{items_summary}"
    )
    sns.publish(
        TopicArn=topic_arn,
        Subject=f"[AgentCore drift] {env} — {report['max_severity']}",
        Message=msg,
    )


def main() -> int:
    plan_json_path = os.environ.get("PLAN_JSON_PATH", "plan.json")
    threshold = os.environ.get("SEVERITY_THRESHOLD", "medium")
    sns_topic = os.environ.get("SNS_TOPIC_ARN", "")
    env = os.environ.get("ENVIRONMENT", "unknown")

    report = analyze_plan(plan_json_path)
    pathlib.Path("drift_report.json").write_text(json.dumps(report, indent=2))

    print(f"[drift_check] env={env} drift={report['drift']} max_severity={report.get('max_severity', 'n/a')} count={report.get('count', 0)}")

    if not report["drift"]:
        print("[drift_check] OK — no hay drift")
        return 0

    if SEVERITY_RANK[report["max_severity"]] < SEVERITY_RANK[threshold]:
        print(f"[drift_check] drift detectado pero severity < threshold ({threshold}) — solo log")
        return 0

    if sns_topic:
        try:
            alert_sns(sns_topic, env, report)
            print(f"[drift_check] alerta publicada a {sns_topic}")
        except Exception as e:
            print(f"[drift_check] WARN: no se pudo publicar SNS: {e}", file=sys.stderr)

    # Drift sobre threshold → exit 1 para que el job aparezca rojo
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

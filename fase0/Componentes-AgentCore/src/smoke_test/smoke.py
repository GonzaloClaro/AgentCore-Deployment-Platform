"""smoke_test: invoca /ping del runtime AgentCore tras apply."""
from __future__ import annotations

import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from utils.aws_client import client


def main() -> int:
    runtime_arn = os.environ["RUNTIME_ARN"]
    payload = os.environ.get("PAYLOAD", '{"prompt":"ping"}')
    expect_status = int(os.environ.get("EXPECT_STATUS", "200"))

    print(f"[smoke_test] runtime={runtime_arn}")
    bac = client("bedrock-agentcore")
    resp = bac.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        payload=payload.encode("utf-8"),
    )
    status = resp["ResponseMetadata"]["HTTPStatusCode"]
    body = resp.get("response", b"").read() if hasattr(resp.get("response"), "read") else resp.get("response", b"")
    body_str = body.decode("utf-8", errors="replace") if isinstance(body, bytes) else str(body)

    report = {"runtime_arn": runtime_arn, "status": status, "body_preview": body_str[:500]}
    pathlib.Path("smoke_report.json").write_text(json.dumps(report, indent=2))
    print(f"[smoke_test] status={status}")

    return 0 if status == expect_status else 1


if __name__ == "__main__":
    raise SystemExit(main())

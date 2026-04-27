"""utils.telemetry — helper opcional para que cualquier script emita un evento.

Uso desde otro componente:
    from utils.telemetry import emit
    emit("validate_manifest.complete", status="success", metadata={"errors": 0})

Si TRACE_ID está en env (heredado), lo usa. Si no, no falla — solo skipea (telemetría
NUNCA debe romper un deploy).
"""
from __future__ import annotations

import datetime
import json
import os

try:
    from utils.aws_client import client
except ImportError:
    client = None


def emit(event_name: str, status: str = "success", metadata: dict | None = None) -> None:
    trace_id = os.environ.get("TRACE_ID")
    log_group = os.environ.get("LOG_GROUP", "/agentcore/pipeline-telemetry")

    if not trace_id or client is None:
        # Sin trace_id o sin AWS client → no emitimos (mejor silencio que falla cascada)
        return

    event = {
        "trace_id": trace_id,
        "event": event_name,
        "status": status,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "stage": os.environ.get("CI_JOB_STAGE"),
        "job_name": os.environ.get("CI_JOB_NAME"),
        "metadata": metadata or {},
    }

    try:
        logs = client("logs")
        try:
            logs.create_log_stream(logGroupName=log_group, logStreamName=trace_id)
        except logs.exceptions.ResourceAlreadyExistsException:
            pass
        logs.put_log_events(
            logGroupName=log_group,
            logStreamName=trace_id,
            logEvents=[{
                "timestamp": int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000),
                "message": json.dumps(event),
            }],
        )
    except Exception:
        # Telemetría falla → silencio. NO bloquea deploy.
        pass

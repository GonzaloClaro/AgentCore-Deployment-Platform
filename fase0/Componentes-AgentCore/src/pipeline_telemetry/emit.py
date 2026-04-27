"""pipeline_telemetry: emite eventos estructurados a CloudWatch Logs.

Acciones:
  - emit_start: genera TRACE_ID, emite "pipeline.start" con metadata del proyecto/branch.
                Escribe TRACE_ID a telemetry.env para que el resto del pipeline lo herede.
  - emit_end:   recolecta status del pipeline via GitLab API, emite "pipeline.end".
  - emit_event: emite un evento custom (typically invocado al final de cada stage por
                otros componentes).

Trace propagation cross-pipeline:
  - upstream (workload pipeline) genera TRACE_ID al inicio.
  - trigger_iac propaga TRACE_ID como CI variable al downstream (agentcore-{env}).
  - downstream emite eventos con el mismo TRACE_ID → correlación end-to-end en CloudWatch.

Estructura del evento (JSON):
  {
    "trace_id": "ulid-or-uuid",
    "event": "pipeline.start | pipeline.end | stage.complete | etc",
    "status": "success | failure | running",
    "timestamp": "ISO 8601",
    "stage": "validate | package | build | ...",
    "ci": { project, pipeline_id, job_id, branch, commit_sha, ... },
    "workload": { capability, name, environment },
    "metadata": { ... }
  }
"""
from __future__ import annotations

import datetime
import json
import os
import pathlib
import sys
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from utils.aws_client import client


def gen_trace_id() -> str:
    """Genera trace ID nuevo. Formato: timestamp-uuid (ordenable cronológicamente)."""
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{ts}-{uuid.uuid4().hex[:12]}"


def ci_context() -> dict:
    """Extrae el contexto CI del runner GitLab."""
    return {
        "project": os.environ.get("CI_PROJECT_PATH"),
        "pipeline_id": os.environ.get("CI_PIPELINE_ID"),
        "job_id": os.environ.get("CI_JOB_ID"),
        "job_name": os.environ.get("CI_JOB_NAME"),
        "stage": os.environ.get("CI_JOB_STAGE"),
        "branch": os.environ.get("CI_COMMIT_BRANCH"),
        "commit_sha": os.environ.get("CI_COMMIT_SHORT_SHA"),
        "runner": os.environ.get("CI_RUNNER_DESCRIPTION"),
        "upstream_pipeline": os.environ.get("UPSTREAM_PIPELINE_ID"),  # set por trigger_iac
        "upstream_project": os.environ.get("UPSTREAM_PROJECT"),
    }


def workload_context() -> dict:
    return {
        "capability": os.environ.get("CAPABILITY"),
        "workload_name": os.environ.get("WORKLOAD_NAME"),
        "environment": os.environ.get("ENVIRONMENT"),
        "kind": os.environ.get("KIND", "agents"),
    }


def emit_to_cloudwatch(log_group: str, trace_id: str, event: dict) -> None:
    """Escribe el evento a CloudWatch Logs. Stream = trace_id para agrupación natural."""
    logs = client("logs")
    log_stream = trace_id

    # Crear log group/stream si no existen (idempotente)
    try:
        logs.create_log_group(logGroupName=log_group)
    except logs.exceptions.ResourceAlreadyExistsException:
        pass
    try:
        logs.create_log_stream(logGroupName=log_group, logStreamName=log_stream)
    except logs.exceptions.ResourceAlreadyExistsException:
        pass

    logs.put_log_events(
        logGroupName=log_group,
        logStreamName=log_stream,
        logEvents=[{
            "timestamp": int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000),
            "message": json.dumps(event),
        }],
    )


def main() -> int:
    action = os.environ.get("ACTION", "emit_event")
    log_group = os.environ.get("LOG_GROUP", "/agentcore/pipeline-telemetry")

    # Generar o heredar trace_id
    trace_id = os.environ.get("TRACE_ID")
    if action == "emit_start" or not trace_id:
        trace_id = gen_trace_id()
        # Escribir a telemetry.env para que GitLab lo propague al resto del pipeline
        pathlib.Path("telemetry.env").write_text(f"TRACE_ID={trace_id}\n")
        print(f"[telemetry] trace_id generado: {trace_id}")
    else:
        # En emit_end / emit_event, trace_id viene heredado del start o del trigger
        pathlib.Path("telemetry.env").write_text(f"TRACE_ID={trace_id}\n")

    event_name = {
        "emit_start": "pipeline.start",
        "emit_end": "pipeline.end",
        "emit_event": os.environ.get("EVENT_NAME", "pipeline.event"),
    }.get(action, "pipeline.event")

    metadata = {}
    try:
        metadata = json.loads(os.environ.get("EVENT_METADATA", "{}"))
    except json.JSONDecodeError:
        metadata = {"_raw": os.environ.get("EVENT_METADATA")}

    event = {
        "trace_id": trace_id,
        "event": event_name,
        "status": os.environ.get("EVENT_STATUS", "success"),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "ci": ci_context(),
        "workload": workload_context(),
        "metadata": metadata,
    }

    pathlib.Path("telemetry_event.json").write_text(json.dumps(event, indent=2))

    # Emit a CloudWatch — si AWS no disponible (local test), seguir adelante
    try:
        emit_to_cloudwatch(log_group, trace_id, event)
        print(f"[telemetry] emit OK: {event_name} ({event['status']}) → {log_group}/{trace_id}")
    except Exception as e:
        print(f"[telemetry] WARN: no se pudo emitir a CloudWatch: {e}", file=sys.stderr)
        # No fallar el job por telemetría (telemetría rota no debe bloquear deploys)
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

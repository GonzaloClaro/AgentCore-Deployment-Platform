"""Tool desplegada como AWS Lambda.

Contrato Lambda estándar:
  def handler(event: dict, context) -> dict
"""
from __future__ import annotations

import json
import logging

logger = logging.getLogger()
logger.setLevel("INFO")


def handler(event: dict, context) -> dict:
    """Lambda handler. Invocada por AgentCore Gateway via gateway target."""
    logger.info("invoked: %s", json.dumps(event)[:500])

    # TODO: lógica de la tool
    return {
        "statusCode": 200,
        "body": json.dumps({"result": "TODO", "echo": event}),
    }

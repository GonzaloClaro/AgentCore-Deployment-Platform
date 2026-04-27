"""Plantilla mínima de MCP server bajo AgentCore Runtime.

Mismo contrato que un agente: POST /invocations, GET /ping, puerto 8080.
El handler implementa el protocolo MCP (Model Context Protocol).
"""
from __future__ import annotations

import os
import logging
from fastapi import FastAPI, Request

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger("mcp")

app = FastAPI(title="mcp-server")


@app.get("/ping")
def ping() -> dict:
    return {"status": "ok"}


@app.post("/invocations")
async def invocations(request: Request) -> dict:
    """Handler MCP. Recibe requests del protocolo MCP y devuelve responses."""
    payload = await request.json()
    method = payload.get("method")
    logger.info("mcp method=%s", method)

    # TODO: implementar el dispatcher MCP (tools/list, tools/call, resources/list, etc.)
    if method == "tools/list":
        return {"tools": []}
    if method == "tools/call":
        return {"content": [{"type": "text", "text": "TODO"}]}
    return {"error": f"method no soportado: {method}"}

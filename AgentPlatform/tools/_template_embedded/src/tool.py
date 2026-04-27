"""Tool embedded — se importa directamente desde el agente.

Convención:
  - Exportar una función `handler(payload: dict) -> dict` o un set de funciones tipadas.
  - El agente las llama via `from tools.<name> import handler` después de horneadas en la imagen.
"""
from __future__ import annotations


def handler(payload: dict) -> dict:
    """Entrypoint de la tool. Recibe payload del agente, devuelve resultado serializable."""
    return {"result": "TODO", "echo": payload}

"""Plantilla mínima de agente para AgentCore Runtime.

Contrato HTTP requerido:
  POST /invocations  → recibe payload del usuario, devuelve respuesta del agente
  GET  /ping         → health check (debe responder 200 OK)

El runtime se sirve con uvicorn en puerto 8080.

═══════════════════════════════════════════════════════════════════════════════
PATRÓN: leer modelos desde env vars (NO hardcodear model_id en el código).

El manifest declara `spec.models[]`. Cada entry produce env vars con prefijo
del alias. Ejemplo manifest:
    spec:
      models:
        - alias: PRIMARY_MODEL
          provider: bedrock
          bedrock: { model_id: anthropic.claude-3-5-sonnet-20241022-v2:0 }
        - alias: FALLBACK_MODEL
          provider: bedrock
          bedrock: { model_id: anthropic.claude-3-5-haiku-20241022-v1:0 }

Produce env vars en runtime:
    PRIMARY_MODEL_ID       = anthropic.claude-3-5-sonnet-20241022-v2:0
    PRIMARY_MODEL_PROVIDER = bedrock
    PRIMARY_MODEL_REGION   = us-east-1
    FALLBACK_MODEL_ID      = anthropic.claude-3-5-haiku-20241022-v1:0
    ...

Cambiar de modelo = MR al manifest + apply. Auditable, declarativo, sin tocar código.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
import logging
import os

import boto3
from fastapi import FastAPI, Request

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger("agent")

app = FastAPI(title="agent")


# ─── Resolución de modelos desde env vars (PATRÓN ESTÁNDAR) ───
# Helper: leer config de un modelo por alias. Devuelve None si no está declarado.
def model_config(alias: str) -> dict | None:
    model_id = os.environ.get(f"{alias}_ID")
    if not model_id:
        return None
    return {
        "id": model_id,
        "provider": os.environ.get(f"{alias}_PROVIDER", "bedrock"),
        "region": os.environ.get(f"{alias}_REGION"),
        # Bedrock-specific
        "inference_profile_arn": os.environ.get(f"{alias}_INFERENCE_PROFILE_ARN"),
        # Azure-specific
        "endpoint": os.environ.get(f"{alias}_ENDPOINT"),
        "deployment": os.environ.get(f"{alias}_DEPLOYMENT"),
        "api_version": os.environ.get(f"{alias}_API_VERSION"),
        "api_key_secret_arn": os.environ.get(f"{alias}_API_KEY_SECRET_ARN"),
    }


# Cache de Azure API keys (no resolver Secrets Manager en cada invocación)
_azure_api_key_cache: dict[str, str] = {}


def get_azure_api_key(secret_arn: str) -> str:
    if secret_arn in _azure_api_key_cache:
        return _azure_api_key_cache[secret_arn]
    sm = boto3.client("secretsmanager")
    resp = sm.get_secret_value(SecretId=secret_arn)
    key = resp["SecretString"]
    _azure_api_key_cache[secret_arn] = key
    return key


# ─── Llamada al modelo ─────────────────────────────────────────────────────
def invoke_model(alias: str, messages: list, **kwargs) -> str:
    cfg = model_config(alias)
    if not cfg:
        raise RuntimeError(f"Modelo '{alias}' no declarado en spec.models del manifest")

    if cfg["provider"] == "bedrock":
        bedrock = boto3.client("bedrock-runtime", region_name=cfg["region"])
        # Usar inference profile si está disponible, sino model_id directo
        model_target = cfg["inference_profile_arn"] or cfg["id"]
        response = bedrock.converse(
            modelId=model_target,
            messages=[{"role": m["role"], "content": [{"text": m["content"]}]} for m in messages],
            inferenceConfig={"maxTokens": kwargs.get("max_tokens", 1024)},
        )
        return response["output"]["message"]["content"][0]["text"]

    elif cfg["provider"] == "azure":
        # Lazy import de openai SDK (no inflar la imagen si solo se usa Bedrock)
        from openai import AzureOpenAI

        client = AzureOpenAI(
            azure_endpoint=cfg["endpoint"],
            api_key=get_azure_api_key(cfg["api_key_secret_arn"]),
            api_version=cfg["api_version"],
        )
        response = client.chat.completions.create(
            model=cfg["deployment"],
            messages=messages,
            max_tokens=kwargs.get("max_tokens", 1024),
        )
        return response.choices[0].message.content

    raise ValueError(f"Provider desconocido: {cfg['provider']}")


# ─── HTTP endpoints ────────────────────────────────────────────────────────
@app.get("/ping")
def ping() -> dict:
    return {
        "status": "ok",
        "models_available": [
            alias.removesuffix("_ID")
            for alias in os.environ
            if alias.endswith("_MODEL_ID")
        ],
    }


@app.post("/invocations")
async def invocations(request: Request) -> dict:
    payload = await request.json()
    prompt = payload.get("prompt", "")
    logger.info("invocation: prompt=%r", prompt[:200])

    # Ejemplo: usar el modelo PRIMARY declarado en el manifest
    response_text = invoke_model(
        alias="PRIMARY_MODEL",
        messages=[
            {"role": "user", "content": prompt},
        ],
    )

    return {"role": "assistant", "content": response_text}

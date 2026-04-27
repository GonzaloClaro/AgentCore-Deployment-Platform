# Base ARM64 para AgentCore Runtime.
# Contrato: puerto 8080, endpoints POST /invocations y GET /ping.
# Build: docker buildx build --platform linux/arm64 -f agent-runtime.Dockerfile .
FROM --platform=linux/arm64 public.ecr.aws/docker/library/python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /app

# Dependencias del sistema mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero para cachear capa
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

# Copiar código del agente
COPY . /app/

# Usuario no-root
RUN useradd -m -u 1000 agent && chown -R agent:agent /app
USER agent

EXPOSE 8080

# El entrypoint del agente debe servir un HTTP server con /invocations y /ping
# (típicamente FastAPI/uvicorn). Default: agent.py expone `app`.
CMD ["python", "-m", "uvicorn", "agent:app", "--host", "0.0.0.0", "--port", "8080"]

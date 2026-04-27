# Base ARM64 para MCP Server bajo AgentCore Runtime.
# Mismo contrato HTTP (puerto 8080, /invocations, /ping); el handler implementa el MCP protocol.
FROM --platform=linux/arm64 public.ecr.aws/docker/library/python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

COPY . /app/

RUN useradd -m -u 1000 mcp && chown -R mcp:mcp /app
USER mcp

EXPOSE 8080
CMD ["python", "-m", "uvicorn", "mcp_server:app", "--host", "0.0.0.0", "--port", "8080"]

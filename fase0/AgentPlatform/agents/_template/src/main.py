"""
Mock agent template for fase 0.
- Solo stdlib (sin FastAPI ni uvicorn — el zip queda en ~3KB)
- HTTP server en 0.0.0.0:8080 (contrato AgentCore Runtime)
- Endpoints: /ping (GET) y /invocations (POST)
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8080


class AgentHandler(BaseHTTPRequestHandler):
    def _json(self, status: int, body: dict) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        if self.path == "/ping":
            self._json(200, {"status": "ok"})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/invocations":
            self._json(404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"_raw": raw}

        prompt = payload.get("prompt") if isinstance(payload, dict) else ""

        # En un agente real, aquí invocás Bedrock con el modelo PRIMARY:
        #
        #   import boto3
        #   bedrock = boto3.client("bedrock-runtime", region_name=os.environ["PRIMARY_MODEL_REGION"])
        #   response = bedrock.converse(
        #       modelId=os.environ["PRIMARY_MODEL_ID"],
        #       messages=[{"role": "user", "content": [{"text": prompt}]}],
        #   )
        #   answer = response["output"]["message"]["content"][0]["text"]

        self._json(
            200,
            {
                "response": f"Echo: {prompt}" if prompt else "Hello from fase 0 agent",
                "model_configured": os.environ.get("PRIMARY_MODEL_ID", "none"),
            },
        )

    def log_message(self, format: str, *args) -> None:
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")


def main() -> None:
    server = HTTPServer(("0.0.0.0", PORT), AgentHandler)
    print(f"Agent listening on 0.0.0.0:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

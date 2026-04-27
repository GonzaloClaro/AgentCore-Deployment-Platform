"""upload_secret: lee CI variable masked y la sube a Secrets Manager."""
from __future__ import annotations

import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from utils.aws_client import client


def main() -> int:
    secret_name = os.environ["SECRET_NAME"]
    value_var = os.environ["VALUE_VAR_NAME"]
    kms_key_id = os.environ.get("KMS_KEY_ID", "alias/agentcore-secrets")
    env = os.environ["ENVIRONMENT"]

    value = os.environ.get(value_var)
    if not value:
        print(f"ERROR: la CI variable {value_var} está vacía o no existe", file=sys.stderr)
        return 2

    full_name = f"agentcore/{env}/{secret_name}"
    sm = client("secretsmanager")
    try:
        resp = sm.create_secret(
            Name=full_name, SecretString=value, KmsKeyId=kms_key_id,
            Tags=[{"Key": "managed-by", "Value": "agentcore-pipeline"}],
        )
        arn = resp["ARN"]
        print(f"[upload_secret] secreto creado: {arn}")
    except sm.exceptions.ResourceExistsException:
        resp = sm.put_secret_value(SecretId=full_name, SecretString=value)
        arn = resp["ARN"]
        print(f"[upload_secret] nueva versión del secreto existente: {arn}")

    pathlib.Path("secret_meta.json").write_text(json.dumps({
        "secret_name": full_name, "secret_arn": arn,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

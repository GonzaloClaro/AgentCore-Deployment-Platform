"""Helpers de boto3 con region default y manejo de errores uniforme."""
from __future__ import annotations

import os
import boto3
from botocore.config import Config

DEFAULT_REGION = os.environ.get("AWS_REGION", "us-east-1")
_BOTO_CONFIG = Config(retries={"max_attempts": 5, "mode": "standard"})


def client(service: str, region: str | None = None):
    return boto3.client(service, region_name=region or DEFAULT_REGION, config=_BOTO_CONFIG)


def account_id() -> str:
    return client("sts").get_caller_identity()["Account"]

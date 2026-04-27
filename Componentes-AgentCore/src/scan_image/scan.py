"""scan_image: escanea imagen ECR con Trivy o Inspector y rompe job si supera severity."""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

SEVERITY_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def scan_with_trivy(image_uri: str) -> dict:
    out = subprocess.check_output(
        ["trivy", "image", "--format", "json", "--quiet", image_uri]
    )
    return json.loads(out)


def scan_with_inspector(image_uri: str) -> dict:
    # Inspector v2 escanea ECR automáticamente; aquí solo consultamos findings
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
    from utils.aws_client import client
    inspector = client("inspector2")
    # En implementación real: filter por imageRepositoryName + imageTag
    return inspector.list_findings().get("findings", [])


def evaluate(report: dict | list, threshold: str) -> tuple[int, list[dict]]:
    threshold_level = SEVERITY_ORDER[threshold.upper()]
    over = []
    if isinstance(report, dict) and "Results" in report:  # trivy
        for result in report["Results"] or []:
            for v in result.get("Vulnerabilities", []) or []:
                if SEVERITY_ORDER.get(v.get("Severity", "LOW").upper(), 0) >= threshold_level:
                    over.append({"id": v.get("VulnerabilityID"), "severity": v["Severity"]})
    elif isinstance(report, list):  # inspector
        for f in report:
            if SEVERITY_ORDER.get(f.get("severity", "LOW").upper(), 0) >= threshold_level:
                over.append({"id": f.get("findingArn"), "severity": f["severity"]})
    return len(over), over


def main() -> int:
    image_uri = os.environ["IMAGE_URI"]
    threshold = os.environ.get("SEVERITY_THRESHOLD", "HIGH")
    scanner = os.environ.get("SCANNER", "trivy")

    print(f"[scan_image] scanner={scanner} image={image_uri} threshold={threshold}")
    if scanner == "trivy":
        report = scan_with_trivy(image_uri)
    else:
        report = scan_with_inspector(image_uri)

    count, items = evaluate(report, threshold)
    pathlib.Path("scan_report.json").write_text(json.dumps({
        "scanner": scanner, "image": image_uri, "threshold": threshold,
        "count_over_threshold": count, "items": items[:50],
    }, indent=2))

    if count > 0:
        print(f"[scan_image] FAIL: {count} vulnerabilidades >= {threshold}")
        return 1
    print("[scan_image] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Trigger Exercise 02 custom (template) model training via REST API after setup.cmd uploads blobs.

Usage (repo root):
  set LAB02_CONTAINER_URL=<full SAS URL printed by setup.cmd>
  python scripts/train_lab02_custom_model.py

Or:
  python scripts/train_lab02_custom_model.py --container-url "https://....blob...?..."
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

API = "2024-11-30"
DEFAULT_MODEL_ID = "mslearn-lab02-forms"


def _load_credentials() -> tuple[str, str]:
    root = Path(__file__).resolve().parents[1]
    env_path = root / ".env"
    if env_path.is_file():
        load_dotenv(env_path)
    load_dotenv()
    endpoint = (
        os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT")
        or os.getenv("DOC_INTELLIGENCE_ENDPOINT")
        or ""
    ).rstrip("/")
    key = os.getenv("DOCUMENT_INTELLIGENCE_KEY") or os.getenv("DOC_INTELLIGENCE_KEY") or ""
    if not endpoint or not key:
        sys.exit("Missing DOCUMENT_INTELLIGENCE_ENDPOINT / DOCUMENT_INTELLIGENCE_KEY in .env")
    return endpoint, key


def _merge_model_id_env(model_id: str) -> None:
    root = Path(__file__).resolve().parents[1]
    env_path = root / ".env"
    if not env_path.is_file():
        sys.exit(f"Missing {env_path}")
    text = env_path.read_text(encoding="utf-8")
    if re.search(r"(?m)^MODEL_ID=", text):
        text = re.sub(r"(?m)^MODEL_ID=.*$", f"MODEL_ID={model_id}", text)
    else:
        text = text.rstrip() + f"\nMODEL_ID={model_id}\n"
    env_path.write_text(text, encoding="utf-8")
    print(f"Wrote MODEL_ID={model_id} to {env_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--container-url",
        default=os.getenv("LAB02_CONTAINER_URL") or os.getenv("LAB02_CONTAINER_SAS"),
        help="Full blob container URL with SAS from setup.cmd output",
    )
    parser.add_argument(
        "--model-id",
        default=os.getenv("LAB02_MODEL_ID") or DEFAULT_MODEL_ID,
        help="New custom model id (unique in this resource)",
    )
    args = parser.parse_args()

    if not args.container_url:
        sys.exit(
            "Pass --container-url or set LAB02_CONTAINER_URL to the SAS URI printed by setup.cmd"
        )

    endpoint, key = _load_credentials()
    build_url = f"{endpoint}/documentintelligence/documentModels:build?api-version={API}"
    body = {
        "modelId": args.model_id,
        "description": "MS Learn Exercise 02 custom extraction (template)",
        "buildMode": "template",
        "azureBlobSource": {"containerUrl": args.container_url},
    }
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/json",
    }

    print(f"Starting build for model {args.model_id!r} (this can take several minutes)...")
    r = requests.post(build_url, headers=headers, json=body, timeout=120)
    if r.status_code not in (200, 202):
        print(r.status_code, r.text[:2000], file=sys.stderr)
        sys.exit(1)

    op_url = r.headers.get("Operation-Location") or r.headers.get("operation-location")
    if not op_url:
        print("No Operation-Location header:", r.text[:1000], file=sys.stderr)
        sys.exit(1)

    poll_headers = {"Ocp-Apim-Subscription-Key": key}
    while True:
        pr = requests.get(op_url, headers=poll_headers, timeout=120)
        if pr.status_code != 200:
            print(pr.status_code, pr.text[:1500], file=sys.stderr)
            sys.exit(1)
        payload = pr.json()
        status = payload.get("status") or payload.get("result", {}).get("status")
        if status in ("succeeded", "Succeeded"):
            print("Build succeeded.")
            break
        if status in ("running", "notStarted", "NotStarted"):
            pct = payload.get("percentCompleted") or payload.get("result", {}).get(
                "percentCompleted"
            )
            print(f"  status={status!r} percent={pct!r} ...")
        elif status in ("failed", "Failed"):
            try:
                print(json.dumps(payload, indent=2)[:8000], file=sys.stderr)
            except Exception:
                print(str(payload)[:8000], file=sys.stderr)
            sys.exit(1)
        time.sleep(5)

    _merge_model_id_env(args.model_id)
    print(
        "Next: python mslearn-ai-document-intelligence/Labfiles/02-custom-document-intelligence/Python/test-model.py"
    )


if __name__ == "__main__":
    main()

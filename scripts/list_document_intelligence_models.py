#!/usr/bin/env python3
"""List custom models on your Document Intelligence resource (uses repo root .env)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# Try GA first, then older API versions / legacy path used by some resources.
_URL_TRIES = [
    ("documentintelligence/documentModels", "2024-11-30"),
    ("documentintelligence/documentModels", "2023-07-31"),
    ("formrecognizer/documentModels", "2023-07-31"),
    ("formrecognizer/documentModels", "2022-08-31"),
]


def main() -> None:
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
        print("Set DOCUMENT_INTELLIGENCE_ENDPOINT and DOCUMENT_INTELLIGENCE_KEY in .env", file=sys.stderr)
        sys.exit(1)

    data = None
    last_err = ""
    for path, ver in _URL_TRIES:
        url = f"{endpoint}/{path}?api-version={ver}"
        r = requests.get(
            url,
            headers={"Ocp-Apim-Subscription-Key": key},
            timeout=60,
        )
        if r.status_code == 200:
            data = r.json()
            break
        last_err = f"{r.status_code} {r.text[:300]}"

    if data is None:
        print("Could not list models:", last_err, file=sys.stderr)
        sys.exit(1)
    models = data.get("value") or data.get("models") or []
    if not models:
        print("No models returned.")
        return

    custom = []
    prebuilt = []
    for m in models:
        mid = m.get("modelId") or m.get("model_id") or ""
        if mid.startswith("prebuilt-"):
            prebuilt.append(m)
        else:
            custom.append(m)

    if custom:
        print("Custom models (use one as MODEL_ID for Exercise 02):\n")
        for m in custom:
            mid = m.get("modelId") or m.get("model_id") or "?"
            desc = m.get("description") or ""
            created = m.get("createdDateTime") or m.get("createdOn") or ""
            print(f"  {mid}")
            if desc:
                print(f"      description: {desc}")
            if created:
                print(f"      created: {created}")
            print()
        print("In repo root .env:\n  MODEL_ID=<id-from-above>\n")
    else:
        print(
            "No custom models on this resource — only built-in (prebuilt-*) models were returned.\n\n"
            "Exercise 02 needs a model you train yourself:\n"
            "  1. Run Labfiles/02-custom-document-intelligence/setup.cmd (storage + upload forms).\n"
            "  2. https://documentintelligence.ai.azure.com/studio -> Custom extraction model -> "
            "create project -> Train.\n"
            "  3. Models page -> copy your model id -> set MODEL_ID in .env.\n"
        )


if __name__ == "__main__":
    main()

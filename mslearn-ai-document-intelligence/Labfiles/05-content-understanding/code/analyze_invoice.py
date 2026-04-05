"""
Exercise 05: Content Understanding REST client (matches Microsoft Learn flow).

Requires:
  - PROJECT_CONNECTION (Azure AI Foundry project connection string)
  - ANALYZER (e.g. contoso-invoice-analyzer)

Install: pip install -r requirements.txt
Run: python analyze_invoice.py [path-or-url-to-invoice.pdf]
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import ConnectionType
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

CU_VERSION = os.getenv("CONTENT_UNDERSTANDING_API_VERSION", "2024-12-01-preview")

_ROOT_ENV = Path(__file__).resolve().parents[4] / ".env"
if _ROOT_ENV.is_file():
    load_dotenv(_ROOT_ENV)
load_dotenv()


def _resolve_invoice_path(name: str) -> Path:
    """Resolve invoice file relative to cwd, this script dir, or script_dir/forms."""
    p = Path(name)
    if p.is_file():
        return p.resolve()
    here = Path(__file__).resolve().parent
    for base in (Path.cwd(), here, here / "forms"):
        candidate = (base / name).resolve()
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"Could not find {name}. Place it next to this script or in a 'forms' folder."
    )


def _print_fields(fields: dict) -> None:
    for field_name, field_data in fields.items():
        if not isinstance(field_data, dict):
            continue
        if "valueNumber" in field_data:
            print(f"{field_name}: {field_data['valueNumber']}")
        elif "valueString" in field_data:
            print(f"{field_name}: {field_data['valueString']}")
        elif field_name == "Items" and "valueArray" in field_data:
            print("Items:")
            for item in field_data["valueArray"]:
                print("  Item:")
                obj = item.get("valueObject") or {}
                for item_field_name, item_field_data in obj.items():
                    if not isinstance(item_field_data, dict):
                        continue
                    if "valueNumber" in item_field_data:
                        print(f"    {item_field_name}: {item_field_data['valueNumber']}")
                    elif "valueString" in item_field_data:
                        print(f"    {item_field_name}: {item_field_data['valueString']}")


def analyze_invoice_bytes(
    data: bytes,
    analyzer: str,
    endpoint: str,
    key: str,
) -> None:
    endpoint = endpoint.rstrip("/")
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/octet-stream",
    }
    url = (
        f"{endpoint}/contentunderstanding/analyzers/{analyzer}"
        f":analyze?api-version={CU_VERSION}"
    )

    print("Submitting document for analysis...")
    response = requests.post(url, headers=headers, data=data, timeout=120)
    if response.status_code not in (200, 202):
        print(response.status_code, response.text)
        response.raise_for_status()

    # Prefer Operation-Location (current REST contract)
    result_url = response.headers.get("Operation-Location") or response.headers.get(
        "operation-location"
    )
    if not result_url and response.content:
        try:
            body = response.json()
            rid = body.get("id") or body.get("requestId")
            if rid:
                result_url = (
                    f"{endpoint}/contentunderstanding/analyzerResults/{rid}"
                    f"?api-version={CU_VERSION}"
                )
        except json.JSONDecodeError:
            pass

    if not result_url:
        print("Unexpected response (no Operation-Location):", response.status_code)
        print(response.text[:2000])
        return

    poll_headers = {"Ocp-Apim-Subscription-Key": key}
    print("Polling for results...")
    while True:
        result_response = requests.get(result_url, headers=poll_headers, timeout=60)
        if result_response.status_code != 200:
            print(result_response.status_code, result_response.text[:2000])
            result_response.raise_for_status()
        payload = result_response.json()
        status = payload.get("status")
        if status in ("Succeeded", "Failed"):
            break
        time.sleep(1.5)

    if status != "Succeeded":
        print("Analysis did not succeed:", json.dumps(payload, indent=2)[:4000])
        return

    print("Analysis succeeded.")
    result_obj = payload.get("result") or {}
    contents = result_obj.get("contents") or []
    for content in contents:
        fields = content.get("fields")
        if isinstance(fields, dict):
            _print_fields(fields)


def main() -> None:
    os.system("cls" if os.name == "nt" else "clear")

    invoice_name = "invoice-1236.pdf"
    if len(sys.argv) > 1:
        invoice_name = sys.argv[1]

    project_connection = os.getenv("PROJECT_CONNECTION")
    analyzer = os.getenv("ANALYZER", "contoso-invoice-analyzer")

    if not project_connection:
        raise SystemExit(
            "Set PROJECT_CONNECTION to your Azure AI Foundry project connection string."
        )

    if invoice_name.lower().startswith("http"):
        print(f"Downloading {invoice_name!r} ...")
        r = requests.get(invoice_name, timeout=120)
        r.raise_for_status()
        data = r.content
    else:
        path = _resolve_invoice_path(invoice_name)
        print(f"Reading {path} ...")
        data = path.read_bytes()

    project_client = AIProjectClient.from_connection_string(
        conn_str=project_connection,
        credential=DefaultAzureCredential(),
    )
    ai_svc_connection = project_client.connections.get_default(
        connection_type=ConnectionType.AZURE_AI_SERVICES,
        include_credentials=True,
    )
    ai_endpoint = ai_svc_connection.endpoint_url
    ai_key = ai_svc_connection.key

    analyze_invoice_bytes(data, analyzer, ai_endpoint, ai_key)


if __name__ == "__main__":
    main()

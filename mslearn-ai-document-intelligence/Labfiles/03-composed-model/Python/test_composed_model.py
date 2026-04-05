"""
Exercise 03: Test a composed model (train 1040 + 1099 models and compose in Studio first).

Set COMPOSED_MODEL_ID to the composed model id from Document Intelligence Studio.
Optional: TEST_DOCUMENT_URL (https...) or TEST_DOCUMENT_PATH (local .pdf).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

_ROOT_ENV = Path(__file__).resolve().parents[4] / ".env"
if _ROOT_ENV.is_file():
    load_dotenv(_ROOT_ENV)
load_dotenv()


def _client() -> DocumentAnalysisClient:
    endpoint = os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT") or os.getenv(
        "DOC_INTELLIGENCE_ENDPOINT"
    )
    key = os.getenv("DOCUMENT_INTELLIGENCE_KEY") or os.getenv("DOC_INTELLIGENCE_KEY")
    if not endpoint or not key:
        raise SystemExit(
            "Set DOCUMENT_INTELLIGENCE_ENDPOINT and DOCUMENT_INTELLIGENCE_KEY in .env"
        )
    return DocumentAnalysisClient(
        endpoint=endpoint, credential=AzureKeyCredential(key)
    )


def main() -> None:
    model_id = os.getenv("COMPOSED_MODEL_ID")
    if not model_id:
        raise SystemExit("Set COMPOSED_MODEL_ID to your composed model id from Studio.")

    test_url = os.getenv("TEST_DOCUMENT_URL")
    test_path = os.getenv("TEST_DOCUMENT_PATH")
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.lower().startswith("http"):
            test_url = arg
        else:
            test_path = arg

    client = _client()

    if test_url:
        print(f"Analyzing URL with composed model {model_id!r}...")
        poller = client.begin_analyze_document_from_url(model_id, test_url)
    elif test_path:
        path = Path(test_path)
        if not path.is_file():
            raise SystemExit(f"File not found: {path}")
        print(f"Analyzing file {path} with composed model {model_id!r}...")
        with path.open("rb") as f:
            poller = client.begin_analyze_document(model_id, f)
    else:
        default = (
            "https://raw.githubusercontent.com/MicrosoftLearning/"
            "mslearn-ai-document-intelligence/main/Labfiles/03-composed-model/"
            "trainingdata/TestDoc/f1040_7.pdf"
        )
        print(
            "No TEST_DOCUMENT_URL / TEST_DOCUMENT_PATH / argv; using default sample URL."
        )
        print(f"URL: {default}")
        poller = client.begin_analyze_document_from_url(model_id, default)

    result = poller.result()
    print(f"Model used: {result.model_id}\n")

    for idx, document in enumerate(result.documents):
        print(f"--- Document {idx + 1} ---")
        print(f"doc_type: {document.doc_type!r}  confidence: {document.confidence}")
        if not document.fields:
            continue
        for name, field in document.fields.items():
            val = field.value if field.value is not None else field.content
            print(f"  {name}: {val!r}  (confidence: {field.confidence})")
    print("Done.")


if __name__ == "__main__":
    main()

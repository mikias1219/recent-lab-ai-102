import os
from pathlib import Path

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

_root_env = Path(__file__).resolve().parents[4] / ".env"
if _root_env.is_file():
    load_dotenv(_root_env)
load_dotenv()

# Prefer root .env names; fall back to lab-specific names.
endpoint = os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT") or os.getenv(
    "DOC_INTELLIGENCE_ENDPOINT", ""
)
key = os.getenv("DOCUMENT_INTELLIGENCE_KEY") or os.getenv("DOC_INTELLIGENCE_KEY", "")

if not endpoint or not key or "<" in endpoint or "<" in key:
    raise SystemExit(
        "Set DOCUMENT_INTELLIGENCE_ENDPOINT and DOCUMENT_INTELLIGENCE_KEY in a .env file "
        "(see workspace .env.example) or export them in your environment."
    )

fileUri = "https://github.com/MicrosoftLearning/mslearn-ai-document-intelligence/blob/main/Labfiles/01-prebuild-models/sample-invoice/sample-invoice.pdf?raw=true"
fileLocale = "en-US"
fileModelId = "prebuilt-invoice"

print(f"\nConnecting to Forms Recognizer at: {endpoint}")
print(f"Analyzing invoice at: {fileUri}")

document_analysis_client = DocumentAnalysisClient(
    endpoint=endpoint, credential=AzureKeyCredential(key)
)

poller = document_analysis_client.begin_analyze_document_from_url(
    fileModelId, fileUri, locale=fileLocale
)

receipts = poller.result()

for idx, receipt in enumerate(receipts.documents):
    vendor_name = receipt.fields.get("VendorName")
    if vendor_name:
        print(f"\nVendor Name: {vendor_name.value}, with confidence {vendor_name.confidence}.")

    customer_name = receipt.fields.get("CustomerName")
    if customer_name:
        print(
            f"Customer Name: '{customer_name.value}', with confidence {customer_name.confidence}."
        )

    invoice_total = receipt.fields.get("InvoiceTotal")
    if invoice_total:
        total = invoice_total.value
        symbol = getattr(total, "currency_symbol", None) or getattr(
            total, "symbol", ""
        )
        amount = getattr(total, "amount", total)
        print(
            f"Invoice Total: '{symbol}{amount}', with confidence {invoice_total.confidence}."
        )

print("\nAnalysis complete.\n")

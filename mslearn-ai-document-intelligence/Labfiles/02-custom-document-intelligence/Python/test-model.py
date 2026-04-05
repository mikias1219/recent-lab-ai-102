import os
import sys
from pathlib import Path

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceNotFoundError
from dotenv import load_dotenv

_root_env = Path(__file__).resolve().parents[4] / ".env"
if _root_env.is_file():
    load_dotenv(_root_env)
load_dotenv()

endpoint = os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT") or os.getenv(
    "DOC_INTELLIGENCE_ENDPOINT"
)
key = os.getenv("DOCUMENT_INTELLIGENCE_KEY") or os.getenv("DOC_INTELLIGENCE_KEY")
model_id = (os.getenv("MODEL_ID") or "").strip()

if not endpoint or not key:
    sys.exit(
        "Set DOCUMENT_INTELLIGENCE_ENDPOINT and DOCUMENT_INTELLIGENCE_KEY in the repo root .env file."
    )

_PLACEHOLDERS = frozenset(
    {
        "",
        "your_model_id",
        "your-trained-model-id",
        "YOUR_MODEL_ID",
    }
)
if not model_id or model_id in _PLACEHOLDERS or model_id.startswith("<"):
    sys.exit(
        "Exercise 02 requires MODEL_ID in your repo root .env — the exact Model ID from "
        "Document Intelligence Studio after you train a custom extraction model on this "
        "same resource.\n\n"
        "Steps:\n"
        "  1. Complete the lab: upload sample-forms, train in Studio (Custom extraction model).\n"
        "  2. Studio -> Models -> copy the model id (e.g. my-form-model).\n"
        "  3. Add to .env:  MODEL_ID=that-id\n\n"
        "The model must exist on the same endpoint as DOCUMENT_INTELLIGENCE_ENDPOINT."
    )

formUrl = "https://github.com/MicrosoftLearning/mslearn-ai-document-intelligence/blob/main/Labfiles/02-custom-document-intelligence/test1.jpg?raw=true"

document_analysis_client = DocumentAnalysisClient(
    endpoint=endpoint, credential=AzureKeyCredential(key)
)

try:
    # Make sure your document's type is included in the list of document types the custom model can analyze
    response = document_analysis_client.begin_analyze_document_from_url(model_id, formUrl)
    result = response.result()
except ResourceNotFoundError as ex:
    err = str(ex)
    if "ModelNotFound" in err or "not found" in err.lower():
        sys.exit(
            f"ModelNotFound for MODEL_ID={model_id!r} on this Document Intelligence resource.\n\n"
            "Fix:\n"
            "  - In https://documentintelligence.ai.azure.com/studio open Models and confirm the id exists "
            "and status is succeeded.\n"
            "  - Use the same Azure resource as your keys (same subscription/resource as this endpoint).\n"
            "  - Update MODEL_ID in repo root .env to match Studio exactly (case-sensitive).\n"
        )
    raise

for idx, document in enumerate(result.documents):
    print("--------Analyzing document #{}--------".format(idx + 1))
    print("Document has type {}".format(document.doc_type))
    print("Document has confidence {}".format(document.confidence))
    print("Document was analyzed by model with ID {}".format(result.model_id))
    for name, field in document.fields.items():
        field_value = field.value if field.value else field.content
        print("Found field '{}' with value '{}' and with confidence {}".format(name, field_value, field.confidence))

print("-----------------------------------")

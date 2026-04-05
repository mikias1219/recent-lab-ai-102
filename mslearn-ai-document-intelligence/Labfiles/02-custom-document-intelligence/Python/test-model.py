import os
from pathlib import Path

from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from dotenv import load_dotenv

_root_env = Path(__file__).resolve().parents[4] / ".env"
if _root_env.is_file():
    load_dotenv(_root_env)
load_dotenv()

endpoint = os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT") or os.getenv(
    "DOC_INTELLIGENCE_ENDPOINT"
)
key = os.getenv("DOCUMENT_INTELLIGENCE_KEY") or os.getenv("DOC_INTELLIGENCE_KEY")
model_id = os.getenv("MODEL_ID")

if not endpoint or not key or not model_id:
    raise SystemExit(
        "Set DOCUMENT_INTELLIGENCE_ENDPOINT, DOCUMENT_INTELLIGENCE_KEY, and MODEL_ID "
        "(your trained custom model id from Document Intelligence Studio)."
    )

formUrl = "https://github.com/MicrosoftLearning/mslearn-ai-document-intelligence/blob/main/Labfiles/02-custom-document-intelligence/test1.jpg?raw=true"

document_analysis_client = DocumentAnalysisClient(
    endpoint=endpoint, credential=AzureKeyCredential(key)
)

# Make sure your document's type is included in the list of document types the custom model can analyze
response = document_analysis_client.begin_analyze_document_from_url(model_id, formUrl)
result = response.result()

for idx, document in enumerate(result.documents):
    print("--------Analyzing document #{}--------".format(idx + 1))
    print("Document has type {}".format(document.doc_type))
    print("Document has confidence {}".format(document.confidence))
    print("Document was analyzed by model with ID {}".format(result.model_id))
    for name, field in document.fields.items():
        field_value = field.value if field.value else field.content
        print("Found field '{}' with value '{}' and with confidence {}".format(name, field_value, field.confidence))

print("-----------------------------------")

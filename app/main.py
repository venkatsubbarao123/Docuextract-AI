import os
from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
import json
import uuid

from .models import ExtractionResponse
from .extractor import get_mock_extraction, run_gemini_extraction

# Automatically load .env file if present
env_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(env_file_path):
    with open(env_file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

app = FastAPI(title="Document Extraction & Structuring Agent API")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory database of processed documents
documents_db: List[ExtractionResponse] = []

# Preload sample documents in the database to showcase the dashboard immediately
def preload_data():
    samples = [
        ExtractionResponse(
            id="doc-001",
            filename="invoice_standard.pdf",
            doc_type="Invoice",
            extracted_data={
                "invoice_number": "INV-2026-9084",
                "invoice_date": "2026-08-15",
                "vendor_name": "Apex Industrial Supplies Ltd.",
                "line_items": [
                    {"description": "Heavy-duty Hydraulic Cylinders (Model H-400)", "quantity": 2.0, "price": 450.00, "amount": 900.00},
                    {"description": "Industrial Sealant Cartridges", "quantity": 10.0, "price": 18.50, "amount": 185.00},
                    {"description": "Premium High-pressure Lubricant (5L)", "quantity": 1.0, "price": 85.00, "amount": 85.00}
                ],
                "subtotal": 1170.00,
                "tax": 117.00,
                "total": 1287.00,
                "due_date": "2026-09-15"
            },
            confidence=0.98,
            review_required=False,
            review_reasons=[],
            status="Verified" # Already approved
        ),
        ExtractionResponse(
            id="doc-002",
            filename="delivery_note_standard.pdf",
            doc_type="Delivery Note",
            extracted_data={
                "delivery_note_id": "DN-88402",
                "delivery_date": "2026-08-18",
                "recipient_name": "Global Manufacturing Plant B",
                "sender_name": "Apex Industrial Supplies Ltd.",
                "po_number": "PO-9940-2026",
                "items": [
                    {"description": "Heavy-duty Hydraulic Cylinders (Model H-400)", "quantity": 2.0, "unit": "pcs"},
                    {"description": "Industrial Sealant Cartridges", "quantity": 10.0, "unit": "boxes"},
                    {"description": "Premium High-pressure Lubricant (5L)", "quantity": 1.0, "unit": "canisters"}
                ],
                "carrier_name": "Swift Logistics Express",
                "received_by": "J. Robertson"
            },
            confidence=0.96,
            review_required=False,
            review_reasons=[],
            status="Pending"
        ),
        ExtractionResponse(
            id="doc-003",
            filename="contract_standard.pdf",
            doc_type="Contract",
            extracted_data={
                "contract_id": "AGR-2026-0042",
                "contract_date": "2026-08-01",
                "parties": [
                    {"name": "Global Manufacturing Corp.", "role": "Client"},
                    {"name": "Apex Industrial Supplies Ltd.", "role": "Contractor"}
                ],
                "effective_date": "2026-08-01",
                "expiration_date": "2027-07-31",
                "contract_amount": 150000.00,
                "contract_type": "Master Services Agreement (MSA)",
                "key_clauses": [
                    "Section 4.1: Net 30 payment terms on all verified invoices.",
                    "Section 8.2: Annual supply volume commitments with 10% volume discount after $50,000 threshold.",
                    "Section 12.1: Termination by either party with 90 days written notice."
                ]
            },
            confidence=0.97,
            review_required=False,
            review_reasons=[],
            status="Pending"
        ),
        ExtractionResponse(
            id="doc-004",
            filename="invoice_blurry_low_quality.jpg",
            doc_type="Invoice",
            extracted_data={
                "invoice_number": "INV-2026-7[BLURRY]",
                "invoice_date": "2026-08-10",
                "vendor_name": "Titan Steel Casting Inc.",
                "line_items": [
                    {"description": "Reinforced Steel Rebars (Grade 60, 20ft)", "quantity": 150.0, "price": 12.00, "amount": 1800.00},
                    {"description": "[UNREADABLE LINE ITEM]", "quantity": 1.0, "price": 0.0, "amount": 0.0}
                ],
                "subtotal": 1800.00,
                "tax": 0.0,
                "total": 0.0,
                "due_date": "2026-09-10"
            },
            confidence=0.52,
            review_required=True,
            review_reasons=[
                "Blurry or smudged scan detected",
                "Extraction confidence (52%) below threshold (75%)",
                "Unreadable line items or missing total values (tax & total read as 0.0)"
            ],
            status="Pending"
        ),
        ExtractionResponse(
            id="doc-005",
            filename="unusual_handwritten_receipt.jpg",
            doc_type="Invoice",
            extracted_data={
                "invoice_number": "REC-994A",
                "invoice_date": "2026-08-20",
                "vendor_name": "Airport Cafe & Catering (Handwritten)",
                "line_items": [
                    {"description": "Catering services - team meeting lunch", "quantity": 1.0, "price": 340.50, "amount": 340.50}
                ],
                "subtotal": 340.50,
                "tax": 17.03,
                "total": 357.53,
                "due_date": None
            },
            confidence=0.68,
            review_required=True,
            review_reasons=[
                "Unusual handwritten receipt format detected",
                "Missing standard fields: Invoice Due Date is not specified",
                "Confidence score (68%) is below threshold"
            ],
            status="Pending"
        ),
        ExtractionResponse(
            id="doc-006",
            filename="unknown_unsupported.pdf",
            doc_type="Unknown",
            extracted_data={},
            confidence=0.15,
            review_required=True,
            review_reasons=[
                "Document format could not be classified",
                "No valid data matching standard schemas found"
            ],
            status="Pending"
        )
    ]
    documents_db.extend(samples)

preload_data()

# ==========================================
# API ENDPOINTS
# ==========================================

@app.post("/api/extract", response_model=ExtractionResponse)
async def extract_document(
    file: UploadFile = File(...),
    api_key: Optional[str] = Form(None)
):
    """Upload and extract document data."""
    contents = await file.read()
    filename = file.filename or ""
    mime_type = file.content_type
    
    # 1. Enforce 50MB File Limit
    if len(contents) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Document exceeds 50 MB upload limit.")
        
    # 2. Check Empty File
    if len(contents) == 0:
        raise HTTPException(status_code=422, detail="Document is empty or unreadable.")
        
    # 3. Check Allowed Extensions
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in {".pdf", ".png", ".jpg", ".jpeg", ".webp"}:
        raise HTTPException(status_code=415, detail="Unsupported document type. Please upload a PDF, PNG, JPG, JPEG, or WEBP file.")
        
    try:
        # Determine extraction engine based on API Key existence (from form or env var)
        effective_api_key = (api_key or "").strip() or os.getenv("GEMINI_API_KEY", "").strip()
        if effective_api_key:
            result = run_gemini_extraction(
                api_key=effective_api_key,
                filename=filename,
                mime_type=mime_type,
                file_bytes=contents
            )
        else:
            result = get_mock_extraction(filename)
            
        # Add to local DB list
        documents_db.insert(0, result) # Put new items first
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents", response_model=List[ExtractionResponse])
async def list_documents(
    doc_type: Optional[str] = None,
    status: Optional[str] = None,
    review_required: Optional[bool] = None,
    search: Optional[str] = None
):
    """Retrieve processed documents with search and filter parameters."""
    filtered = documents_db
    
    if doc_type:
        filtered = [d for d in filtered if d.doc_type.lower() == doc_type.lower()]
        
    if status:
        filtered = [d for d in filtered if d.status.lower() == status.lower()]
        
    if review_required is not None:
        filtered = [d for d in filtered if d.review_required == review_required]
        
    if search:
        search_lower = search.lower()
        filtered = [
            d for d in filtered 
            if search_lower in d.filename.lower() or search_lower in d.doc_type.lower()
        ]
        
    return filtered


@app.post("/api/documents/{doc_id}/verify", response_model=ExtractionResponse)
async def verify_document(doc_id: str, updated_data: Dict[str, Any]):
    """Approve extraction results, updating the document with verified fields."""
    for doc in documents_db:
        if doc.id == doc_id:
            doc.extracted_data = updated_data
            doc.status = "Verified"
            doc.review_required = False
            doc.review_reasons = []
            return doc
            
    raise HTTPException(status_code=404, detail="Document not found")


@app.get("/api/stats")
async def get_stats():
    """Calculate extraction analytics for the dashboard."""
    total = len(documents_db)
    needs_review = sum(1 for d in documents_db if d.review_required)
    verified = sum(1 for d in documents_db if d.status == "Verified")
    
    # Calculate avg confidence of classified files (excluding unknowns if you wish, or all)
    avg_conf = 0.0
    if total > 0:
        avg_conf = sum(d.confidence for d in documents_db) / total
        
    type_counts = {"Invoice": 0, "Delivery Note": 0, "Contract": 0, "Unknown": 0}
    for d in documents_db:
        if d.doc_type in type_counts:
            type_counts[d.doc_type] += 1
        else:
            type_counts["Unknown"] += 1
            
    return {
        "total_documents": total,
        "needs_review": needs_review,
        "verified": verified,
        "average_confidence": round(avg_conf, 2),
        "type_breakdown": type_counts
    }


# ==========================================
# STATIC FRONTEND ROUTES
# ==========================================

# Make sure directory structures are safe
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)

# Mount static folder
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def get_index():
    """Return the frontend dashboard."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"detail": "Dashboard index.html not found. Please implement frontend files."}

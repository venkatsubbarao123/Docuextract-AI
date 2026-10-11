import os
from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
import json
import uuid

from .models import ExtractionResponse, InvoiceSchema, DeliveryNoteSchema, ContractSchema
from .extractor import run_document_extraction, get_mock_extraction
from .database import init_db, save_document, get_document_by_id, get_all_documents, get_stats_data

# Automatically load .env file if present
env_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(env_file_path):
    with open(env_file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

app = FastAPI(title="DocuExtract AI - Intelligent Document Extraction Agent")

# Initialize SQLite database
init_db()

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def preload_data_if_empty():
    """Populates demo fixture queue only on first run if database is empty."""
    existing = get_all_documents()
    if existing:
        return
        
    samples = [
        ExtractionResponse(
            id="doc-001",
            filename="invoice_standard.pdf",
            doc_type="Invoice",
            extracted_data={
                "invoice_number": "INV-2026-9084",
                "invoice_date": "2026-08-15",
                "vendor_name": "Apex Industrial Supplies Ltd.",
                "currency": "USD",
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
            classification_confidence=0.99,
            review_required=False,
            review_reasons=[],
            status="Verified",
            engine_used="Mock Mode"
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
            classification_confidence=0.98,
            review_required=False,
            review_reasons=[],
            status="Verified",
            engine_used="Mock Mode"
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
                "currency": "USD",
                "contract_type": "Master Services Agreement (MSA)",
                "key_clauses": [
                    "Section 4.1: Net 30 payment terms on all verified invoices.",
                    "Section 8.2: Annual supply volume commitments with 10% volume discount after $50,000 threshold.",
                    "Section 12.1: Termination by either party with 90 days written notice."
                ]
            },
            confidence=0.97,
            classification_confidence=0.99,
            review_required=False,
            review_reasons=[],
            status="Verified",
            engine_used="Mock Mode"
        ),
        ExtractionResponse(
            id="doc-004",
            filename="invoice_blurry_low_quality.jpg",
            doc_type="Invoice",
            extracted_data={
                "invoice_number": "INV-2026-7[BLURRY]",
                "invoice_date": "2026-08-10",
                "vendor_name": "Titan Steel Casting Inc.",
                "currency": "USD",
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
            classification_confidence=0.75,
            review_required=True,
            review_reasons=[
                "Blurry or smudged scan detected",
                "Extraction confidence below threshold (70%)",
                "Unreadable line items or missing total values (tax & total read as 0.0)"
            ],
            status="Pending",
            engine_used="Mock Mode"
        ),
        ExtractionResponse(
            id="doc-005",
            filename="unusual_handwritten_receipt.jpg",
            doc_type="Invoice",
            extracted_data={
                "invoice_number": "REC-994A",
                "invoice_date": "2026-08-20",
                "vendor_name": "Airport Cafe & Catering (Handwritten Receipt)",
                "currency": "USD",
                "line_items": [
                    {"description": "Catering services - team meeting lunch", "quantity": 1.0, "price": 340.50, "amount": 340.50}
                ],
                "subtotal": 340.50,
                "tax": 17.03,
                "total": 357.53,
                "due_date": None
            },
            confidence=0.68,
            classification_confidence=0.82,
            review_required=True,
            review_reasons=[
                "Unusual handwritten receipt format detected",
                "Missing standard fields: Invoice Due Date is not specified",
                "Confidence score (68%) is below threshold"
            ],
            status="Pending",
            engine_used="Mock Mode"
        ),
        ExtractionResponse(
            id="doc-006",
            filename="unknown_unsupported.pdf",
            doc_type="Unknown",
            extracted_data={},
            confidence=0.15,
            classification_confidence=0.15,
            review_required=True,
            review_reasons=[
                "Document format could not be classified",
                "No valid data matching standard schemas found"
            ],
            status="Pending",
            engine_used="Mock Mode"
        )
    ]
    for s in samples:
        save_document(s)

preload_data_if_empty()

# Backward compatibility alias for tests
documents_db = get_all_documents()

# ==========================================
# API ENDPOINTS
# ==========================================

@app.get("/health")
@app.get("/api/health")
async def health_check():
    """Health readiness probe for Render and orchestrators."""
    has_api_key = bool(os.getenv("GEMINI_API_KEY", "").strip())
    return {
        "status": "healthy",
        "gemini_api_configured": has_api_key,
        "database": "sqlite_ready",
        "default_engine": "Local Parser"
    }

@app.get("/api/config")
async def get_config():
    """Returns server-level configuration flags for frontend initialization."""
    has_api_key = bool(os.getenv("GEMINI_API_KEY", "").strip())
    return {
        "has_server_api_key": has_api_key,
        "default_engine": "Local Parser"
    }

@app.post("/api/extract", response_model=ExtractionResponse)
async def extract_document(
    file: UploadFile = File(...),
    api_key: Optional[str] = Form(None)
):
    """Upload and extract real document data with validation."""
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
        # Determine effective API Key
        effective_api_key = (api_key or "").strip() or os.getenv("GEMINI_API_KEY", "").strip()

        # Check if this is a canned gallery fixture name
        if filename in {"invoice_standard.pdf", "delivery_note_standard.pdf", "contract_standard.pdf", "invoice_blurry_low_quality.jpg", "unusual_handwritten_receipt.jpg", "unknown_unsupported.pdf"}:
            result = get_mock_extraction(filename)
        else:
            # Process actual uploaded document
            result = run_document_extraction(
                api_key=effective_api_key,
                filename=filename,
                mime_type=mime_type,
                file_bytes=contents
            )
            
        # Persist document to SQLite database
        save_document(result)
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
    """Retrieve processed documents from persistent storage."""
    return get_all_documents(
        doc_type=doc_type,
        status=status,
        review_required=review_required,
        search=search
    )

@app.get("/api/documents/{doc_id}", response_model=ExtractionResponse)
async def get_document(doc_id: str):
    """Retrieve single document by ID."""
    doc = get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@app.post("/api/documents/{doc_id}/verify", response_model=ExtractionResponse)
async def verify_document(doc_id: str, updated_data: Dict[str, Any]):
    """Approve extraction results and validate schema before saving."""
    doc = get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Validate against target schema
    try:
        if doc.doc_type == "Invoice":
            InvoiceSchema(**updated_data)
        elif doc.doc_type == "Delivery Note":
            DeliveryNoteSchema(**updated_data)
        elif doc.doc_type == "Contract":
            ContractSchema(**updated_data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")

    doc.extracted_data = updated_data
    doc.status = "Verified"
    doc.review_required = False
    doc.review_reasons = []
    
    # Persist update
    save_document(doc)
    return doc

@app.get("/api/stats")
async def get_stats():
    """Calculate extraction analytics from persistent database."""
    return get_stats_data()

# ==========================================
# STATIC FRONTEND ROUTES
# ==========================================

static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def get_index():
    """Return the frontend dashboard."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"detail": "Dashboard index.html not found. Please implement frontend files."}

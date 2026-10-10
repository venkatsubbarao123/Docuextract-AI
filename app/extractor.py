import os
import uuid
import base64
import json
import urllib.request
import urllib.error
import random
import copy
import time
from typing import Dict, Any, Tuple, Optional, List
from .models import InvoiceSchema, DeliveryNoteSchema, ContractSchema, ExtractionResponse
from .parser import (
    extract_text_from_file,
    parse_deterministic_invoice,
    parse_deterministic_delivery_note,
    parse_deterministic_contract
)

# ==========================================
# MOCK / SAMPLE FIXTURES (For UI Showcase only)
# ==========================================

MOCK_INVOICE_STANDARD = {
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
}

MOCK_DELIVERY_NOTE_STANDARD = {
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
}

MOCK_CONTRACT_STANDARD = {
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
}

MOCK_INVOICE_BLURRY = {
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
}

MOCK_UNUSUAL_RECEIPT = {
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
}

def classify_by_filename(filename: str) -> str:
    """Helper to classify mock documents by filename keywords."""
    fn_lower = filename.lower()
    if "invoice" in fn_lower or "bill" in fn_lower or "inv" in fn_lower:
        return "Invoice"
    elif "delivery" in fn_lower or "note" in fn_lower or "dn-" in fn_lower:
        return "Delivery Note"
    elif "contract" in fn_lower or "agreement" in fn_lower or "agr" in fn_lower or "lease" in fn_lower:
        return "Contract"
    else:
        return "Unknown"

def classify_by_content(text: str, filename: str = "") -> Tuple[str, float]:
    """Classifies a document primarily using its extracted text content, with filename as secondary signal."""
    t_lower = text.lower()
    
    inv_score = 0
    dn_score = 0
    cnt_score = 0

    # Content evidence
    if "invoice" in t_lower: inv_score += 4
    if "subtotal" in t_lower or "amount due" in t_lower or "grand total" in t_lower: inv_score += 3
    if "tax" in t_lower or "gst" in t_lower or "cgst" in t_lower or "sgst" in t_lower or "vat" in t_lower: inv_score += 3
    if "bill to" in t_lower or "due date" in t_lower: inv_score += 2

    if "delivery note" in t_lower or "delivery order" in t_lower or "despatch" in t_lower: dn_score += 5
    if "goods received" in t_lower or "received by" in t_lower: dn_score += 3
    if "carrier" in t_lower or "shipped via" in t_lower: dn_score += 2
    if "packages" in t_lower or "cartons" in t_lower: dn_score += 2

    if "agreement" in t_lower or "contract" in t_lower: cnt_score += 4
    if "parties" in t_lower or "between" in t_lower and "hereinafter" in t_lower: cnt_score += 4
    if "effective date" in t_lower or "termination" in t_lower or "governing law" in t_lower: cnt_score += 3
    if "clause" in t_lower or "indemnity" in t_lower or "witnesseth" in t_lower: cnt_score += 3

    # Filename supporting signal (weight: 1)
    fn_lower = filename.lower()
    if "invoice" in fn_lower or "bill" in fn_lower: inv_score += 1
    if "delivery" in fn_lower or "note" in fn_lower or "dn" in fn_lower: dn_score += 1
    if "contract" in fn_lower or "agreement" in fn_lower: cnt_score += 1

    max_score = max(inv_score, dn_score, cnt_score)
    if max_score < 3:
        # Fall back to filename if content gave no signal
        fn_type = classify_by_filename(filename)
        return fn_type, (0.75 if fn_type != "Unknown" else 0.20)

    if inv_score == max_score:
        return "Invoice", min(0.98, 0.70 + (inv_score * 0.03))
    elif dn_score == max_score:
        return "Delivery Note", min(0.98, 0.70 + (dn_score * 0.03))
    elif cnt_score == max_score:
        return "Contract", min(0.98, 0.70 + (cnt_score * 0.03))
    
    return "Unknown", 0.20

def get_mock_extraction(filename: str) -> ExtractionResponse:
    """Simulates document extraction for the canned sample gallery."""
    doc_id = str(uuid.uuid4())[:8]
    fn_lower = filename.lower()

    if "invoice_standard" in fn_lower:
        return ExtractionResponse(
            id=doc_id,
            filename=filename,
            doc_type="Invoice",
            extracted_data=copy.deepcopy(MOCK_INVOICE_STANDARD),
            confidence=0.98,
            classification_confidence=0.99,
            review_required=False,
            review_reasons=[],
            status="Pending",
            engine_used="Mock Mode"
        )
    elif "delivery_note_standard" in fn_lower:
        return ExtractionResponse(
            id=doc_id,
            filename=filename,
            doc_type="Delivery Note",
            extracted_data=copy.deepcopy(MOCK_DELIVERY_NOTE_STANDARD),
            confidence=0.96,
            classification_confidence=0.98,
            review_required=False,
            review_reasons=[],
            status="Pending",
            engine_used="Mock Mode"
        )
    elif "contract_standard" in fn_lower:
        return ExtractionResponse(
            id=doc_id,
            filename=filename,
            doc_type="Contract",
            extracted_data=copy.deepcopy(MOCK_CONTRACT_STANDARD),
            confidence=0.97,
            classification_confidence=0.99,
            review_required=False,
            review_reasons=[],
            status="Pending",
            engine_used="Mock Mode"
        )
    elif "blurry" in fn_lower or "low_quality" in fn_lower:
        return ExtractionResponse(
            id=doc_id,
            filename=filename,
            doc_type="Invoice",
            extracted_data=copy.deepcopy(MOCK_INVOICE_BLURRY),
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
        )
    elif "unusual" in fn_lower or "receipt" in fn_lower:
        return ExtractionResponse(
            id=doc_id,
            filename=filename,
            doc_type="Invoice",
            extracted_data=copy.deepcopy(MOCK_UNUSUAL_RECEIPT),
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
        )
    else:
        return ExtractionResponse(
            id=doc_id,
            filename=filename,
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

# ==========================================
# GEMINI LIVE API ENGINE WITH RETRIES & BACKOFF
# ==========================================

def call_gemini_api(api_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to perform HTTP POST to Google Gemini API with error distinction, backoff, and model fallback."""
    models = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.5-flash", "gemini-flash-latest"]
    last_err = None
    headers = {"Content-Type": "application/json"}
    
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        # Retry loop for transient issues (503, 429)
        max_retries = 2
        for attempt in range(max_retries):
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=20) as response:
                    res_body = response.read().decode("utf-8")
                    return json.loads(res_body)
            except urllib.error.HTTPError as e:
                err_msg = e.read().decode("utf-8", errors="ignore")
                try:
                    err_json = json.loads(err_msg)
                    message = err_json.get("error", {}).get("message", err_msg)
                except Exception:
                    message = err_msg
                    
                # Do not retry permanent client errors (400, 401, 403, 404)
                if e.code in (400, 401, 403, 404):
                    last_err = f"Gemini API Error (HTTP {e.code}): {message}"
                    break
                elif e.code == 429:
                    last_err = "Gemini API Quota/Rate Limit Exceeded (HTTP 429). Please check your quota or wait."
                    time.sleep(1.0 + random.random() * 0.5)
                elif e.code == 503:
                    last_err = f"Gemini API Service Temporarily Unavailable (HTTP 503): {message}"
                    time.sleep(1.0 + random.random() * 0.5)
                else:
                    last_err = f"Gemini API Error (HTTP {e.code}): {message}"
                    break
            except Exception as e:
                last_err = f"Network connection error to Gemini: {str(e)}"
                break
            
    raise Exception(f"Gemini API call failed: {last_err}")

# ==========================================
# HYBRID EXTRACTION (AI + OCR / DETERMINISTIC PARSER)
# ==========================================

def run_document_extraction(
    api_key: Optional[str],
    filename: str,
    mime_type: str,
    file_bytes: bytes
) -> ExtractionResponse:
    """Executes end-to-end document processing:
    1. Extracts text from PDF or raw bytes.
    2. Uses Gemini Multimodal API if an API key is present.
    3. If Gemini is unavailable, uses deterministic parser on actual document contents.
    4. Never returns canned demo fixtures for real user files.
    """
    doc_id = str(uuid.uuid4())[:8]
    raw_text = extract_text_from_file(filename, mime_type, file_bytes)

    # 1. Determine classification from content first
    doc_type, class_conf = classify_by_content(raw_text, filename)

    # 2. Try Gemini Live API if API key is supplied
    if api_key and api_key.strip():
        try:
            return _execute_gemini_extraction(
                api_key=api_key.strip(),
                doc_id=doc_id,
                filename=filename,
                mime_type=mime_type,
                file_bytes=file_bytes,
                initial_doc_type=doc_type,
                initial_class_conf=class_conf,
                raw_text=raw_text
            )
        except Exception as e:
            # Fall back to deterministic parsing with explicit warning
            return _execute_deterministic_fallback(
                doc_id=doc_id,
                filename=filename,
                raw_text=raw_text,
                doc_type=doc_type,
                class_conf=class_conf,
                fallback_reason=f"Gemini AI unavailable ({str(e)}). Processed via deterministic parser."
            )
    else:
        # No API Key provided: process document using deterministic parser
        return _execute_deterministic_fallback(
            doc_id=doc_id,
            filename=filename,
            raw_text=raw_text,
            doc_type=doc_type,
            class_conf=class_conf,
            fallback_reason="Gemini API key not configured. Processed via local deterministic parser."
        )

def _execute_gemini_extraction(
    api_key: str,
    doc_id: str,
    filename: str,
    mime_type: str,
    file_bytes: bytes,
    initial_doc_type: str,
    initial_class_conf: float,
    raw_text: str
) -> ExtractionResponse:
    """Executes Gemini Multimodal classification and extraction."""
    base64_data = base64.b64encode(file_bytes).decode("utf-8")
    
    if not mime_type or mime_type == "application/octet-stream":
        if filename.endswith(".pdf"):
            mime_type = "application/pdf"
        elif filename.endswith(".png"):
            mime_type = "image/png"
        else:
            mime_type = "image/jpeg"

    # Step 1: Multimodal Classification
    classify_prompt = (
        "Analyze the provided document (PDF or image). Classify it into one of these exact categories:\n"
        "1. 'Invoice'\n2. 'Delivery Note'\n3. 'Contract'\n4. 'Unknown'\n\n"
        "Output ONLY the category name."
    )
    classify_payload = {
        "contents": [{
            "parts": [
                {"inlineData": {"mimeType": mime_type, "data": base64_data}},
                {"text": classify_prompt}
            ]
        }]
    }

    doc_type = initial_doc_type
    class_conf = initial_class_conf
    try:
        c_res = call_gemini_api(api_key, classify_payload)
        candidate_parts = c_res.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        c_text = "".join([p.get("text", "") for p in candidate_parts if isinstance(p, dict)]).strip()
        for candidate in ["Invoice", "Delivery Note", "Contract"]:
            if candidate.lower() in c_text.lower():
                doc_type = candidate
                class_conf = 0.95
                break
        if "unknown" in c_text.lower():
            doc_type = "Unknown"
            class_conf = 0.90
    except Exception:
        # Keep initial content-based classification
        pass

    if doc_type == "Unknown":
        return ExtractionResponse(
            id=doc_id,
            filename=filename,
            doc_type="Unknown",
            extracted_data={},
            confidence=0.20,
            classification_confidence=class_conf,
            review_required=True,
            review_reasons=["Document classified as Unknown/Unsupported type."],
            status="Pending"
        )

    # Step 2: Extraction Prompt with JSON output instruction
    if doc_type == "Invoice":
        extract_prompt = (
            "You are an expert document extraction system. Analyze the document and extract structured JSON matching this schema:\n"
            "{\n"
            '  "invoice_number": "string (mandatory)",\n'
            '  "invoice_date": "string (YYYY-MM-DD or raw date)",\n'
            '  "vendor_name": "string (mandatory)",\n'
            '  "buyer_name": "string or null",\n'
            '  "due_date": "string or null",\n'
            '  "currency": "string (INR, USD, EUR, etc. - detect accurately from symbols ₹, $, etc.)",\n'
            '  "line_items": [{"description": "string", "quantity": number, "price": number, "amount": number}],\n'
            '  "subtotal": number,\n'
            '  "tax": number,\n'
            '  "cgst": number or null,\n'
            '  "sgst": number or null,\n'
            '  "total": number\n'
            "}\n"
            "DO NOT substitute default or demo data. Extract the exact values present in the document. "
            "Output ONLY valid JSON."
        )
    elif doc_type == "Delivery Note":
        extract_prompt = (
            "Extract structured JSON matching this schema:\n"
            "{\n"
            '  "delivery_note_id": "string",\n'
            '  "delivery_date": "string",\n'
            '  "recipient_name": "string",\n'
            '  "sender_name": "string",\n'
            '  "po_number": "string or null",\n'
            '  "items": [{"description": "string", "quantity": number, "unit": "string"}],\n'
            '  "carrier_name": "string or null",\n'
            '  "received_by": "string or null"\n'
            "}\n"
            "Extract actual document values only. Output ONLY valid JSON."
        )
    else:  # Contract
        extract_prompt = (
            "Extract structured JSON matching this schema:\n"
            "{\n"
            '  "contract_id": "string",\n'
            '  "contract_date": "string",\n'
            '  "parties": [{"name": "string", "role": "string"}],\n'
            '  "effective_date": "string",\n'
            '  "expiration_date": "string or null",\n'
            '  "contract_amount": number or null,\n'
            '  "currency": "string or null",\n'
            '  "contract_type": "string",\n'
            '  "key_clauses": ["string"]\n'
            "}\n"
            "Extract actual document values only. Output ONLY valid JSON."
        )

    extract_payload = {
        "contents": [{
            "parts": [
                {"inlineData": {"mimeType": mime_type, "data": base64_data}},
                {"text": extract_prompt}
            ]
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    ext_res = call_gemini_api(api_key, extract_payload)
    candidate_parts = ext_res.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    ext_text = "".join([p.get("text", "") for p in candidate_parts if isinstance(p, dict)]).strip()

    # Clean markdown if present
    if ext_text.startswith("```"):
        lines = ext_text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        ext_text = "\n".join(lines).strip()

    extracted_data = json.loads(ext_text)

    # Step 3: Validate and score confidence
    confidence, review_required, review_reasons = _evaluate_extraction_confidence(doc_type, extracted_data, filename)

    return ExtractionResponse(
        id=doc_id,
        filename=filename,
        doc_type=doc_type,
        extracted_data=extracted_data,
        confidence=round(confidence, 2),
        classification_confidence=round(class_conf, 2),
        review_required=review_required,
        review_reasons=review_reasons,
        status="Pending",
        engine_used="Gemini AI"
    )

def _execute_deterministic_fallback(
    doc_id: str,
    filename: str,
    raw_text: str,
    doc_type: str,
    class_conf: float,
    fallback_reason: str
) -> ExtractionResponse:
    """Parses actual document text using deterministic OCR heuristics without fabricating dummy data."""
    extracted_data = {}
    review_reasons = [fallback_reason]
    
    if not raw_text or len(raw_text.strip()) < 10:
        return ExtractionResponse(
            id=doc_id,
            filename=filename,
            doc_type=doc_type,
            extracted_data={},
            confidence=0.20,
            classification_confidence=round(class_conf, 2),
            review_required=True,
            review_reasons=[fallback_reason, "No extractable text found in document. Manual entry or visual inspection required."],
            status="Pending"
        )

    if doc_type == "Invoice":
        extracted_data = parse_deterministic_invoice(raw_text)
    elif doc_type == "Delivery Note":
        extracted_data = parse_deterministic_delivery_note(raw_text)
    elif doc_type == "Contract":
        extracted_data = parse_deterministic_contract(raw_text)

    confidence, review_required, eval_reasons = _evaluate_extraction_confidence(doc_type, extracted_data, filename)
    # Mark review_required as True for all fallback pipeline extractions
    review_required = True
    review_reasons.extend(eval_reasons)

    return ExtractionResponse(
        id=doc_id,
        filename=filename,
        doc_type=doc_type,
        extracted_data=extracted_data,
        confidence=round(min(0.85, confidence), 2),
        classification_confidence=round(class_conf, 2),
        review_required=review_required,
        review_reasons=review_reasons,
        status="Pending",
        engine_used="Local Parser"
    )

def _evaluate_extraction_confidence(doc_type: str, data: Dict[str, Any], filename: str) -> Tuple[float, bool, List[str]]:
    """Calculates factual confidence and review flags based on schema completeness and arithmetic consistency."""
    confidence = 0.95
    review_reasons = []
    
    if doc_type == "Invoice":
        if not data.get("invoice_number"):
            review_reasons.append("Invoice Number is missing or unreadable")
            confidence -= 0.15
        if not data.get("vendor_name"):
            review_reasons.append("Vendor Name is missing or unreadable")
            confidence -= 0.15
        if not data.get("line_items"):
            review_reasons.append("No line items could be extracted")
            confidence -= 0.20
        else:
            # Check line item quantity * price == amount
            for idx, item in enumerate(data.get("line_items", [])):
                q = float(item.get("quantity") or 0.0)
                p = float(item.get("price") or 0.0)
                amt = float(item.get("amount") or 0.0)
                if q > 0 and p > 0 and amt > 0:
                    expected_amt = round(q * p, 2)
                    if abs(amt - expected_amt) > 0.05:
                        review_reasons.append(f"Line item {idx + 1} discrepancy: {q} x {p} = {expected_amt}, but extracted amount is {amt}")
                        confidence -= 0.10
                        break
            
        subtotal = float(data.get("subtotal") or 0.0)
        tax = float(data.get("tax") or 0.0)
        total = float(data.get("total") or 0.0)
        cgst = data.get("cgst")
        sgst = data.get("sgst")
        
        # Check CGST + SGST == total tax if both present
        if cgst is not None and sgst is not None and tax > 0:
            cgst_f = float(cgst)
            sgst_f = float(sgst)
            if abs((cgst_f + sgst_f) - tax) > 0.05:
                review_reasons.append(f"Tax breakdown discrepancy: CGST ({cgst_f}) + SGST ({sgst_f}) = {round(cgst_f + sgst_f, 2)} does not equal Total Tax ({tax})")
                confidence -= 0.10

        if total == 0.0 and subtotal == 0.0:
            review_reasons.append("Financial amounts could not be extracted (Total is 0.0)")
            confidence -= 0.25
        elif subtotal > 0 and abs(total - (subtotal + tax)) > 1.5:
            review_reasons.append(f"Arithmetic discrepancy: Subtotal ({subtotal}) + Tax ({tax}) does not equal Total ({total})")
            confidence -= 0.15

    elif doc_type == "Delivery Note":
        if not data.get("delivery_note_id"):
            review_reasons.append("Delivery Note ID is missing")
            confidence -= 0.15
        if not data.get("recipient_name"):
            review_reasons.append("Recipient Name is missing")
            confidence -= 0.15
        if not data.get("items"):
            review_reasons.append("Delivered items list is empty")
            confidence -= 0.25

    elif doc_type == "Contract":
        if not data.get("contract_id"):
            review_reasons.append("Contract ID is missing")
            confidence -= 0.15
        parties = data.get("parties", [])
        if len(parties) < 2:
            review_reasons.append("Fewer than two contracting parties identified")
            confidence -= 0.20

    if "blurry" in filename.lower() or "low_quality" in filename.lower():
        confidence -= 0.20
        review_reasons.append("Low-quality / blurry document flag detected")

    confidence = max(0.10, min(0.99, confidence))
    review_required = (confidence < 0.75) or (len(review_reasons) > 0)
    
    return confidence, review_required, review_reasons

# Backward compatibility alias
def run_gemini_extraction(api_key: str, filename: str, mime_type: str, file_bytes: bytes) -> ExtractionResponse:
    return run_document_extraction(api_key, filename, mime_type, file_bytes)

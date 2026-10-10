import re
import io
from typing import Dict, Any, List, Optional, Tuple

try:
    import pypdf
except ImportError:
    pypdf = None

def extract_text_from_file(filename: str, mime_type: str, file_bytes: bytes) -> str:
    """Extracts raw text from PDF or text payloads. Returns empty string for pure image binaries."""
    text = ""
    # 1. Try PyPDF if PDF
    if filename.lower().endswith(".pdf") or "pdf" in (mime_type or "").lower():
        if pypdf:
            try:
                reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                pages_text = []
                for p in reader.pages:
                    extracted = p.extract_text()
                    if extracted:
                        pages_text.append(extracted)
                text = "\n".join(pages_text).strip()
            except Exception:
                pass
                
    # 2. Try utf-8 decode (for text-based or test fixtures)
    if not text:
        try:
            decoded = file_bytes.decode("utf-8", errors="ignore").strip()
            # If at least 30% readable characters, treat as text
            if len(decoded) > 20 and any(c.isalpha() for c in decoded):
                text = decoded
        except Exception:
            pass

    return text

def parse_deterministic_invoice(text: str) -> Dict[str, Any]:
    """Deterministically extracts structured invoice fields from text."""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    
    # 1. Currency
    currency = "USD"
    if re.search(r'(?:₹|INR|Rupees|Rs\.?)', text, re.IGNORECASE):
        currency = "INR"
    elif re.search(r'(?:€|EUR|Euro)', text, re.IGNORECASE):
        currency = "EUR"
    elif re.search(r'(?:£|GBP|Pounds)', text, re.IGNORECASE):
        currency = "GBP"

    # 2. Invoice Number
    inv_num_match = re.search(r'(?:Invoice\s*(?:Number|No\.?|#))\s*[:#\-]?\s*([A-Za-z0-9\-_/]+)', text, re.IGNORECASE)
    if not inv_num_match:
        inv_num_match = re.search(r'\bINV[A-Za-z0-9\-_/]+', text, re.IGNORECASE)
    invoice_number = inv_num_match.group(1).strip() if inv_num_match else ""

    # 3. Vendor Name
    vendor_name = ""
    vendor_match = re.search(r'(?:Vendor|Supplier|From|Billed\s*By)\s*[:\-]\s*([^\n\r,]+)', text, re.IGNORECASE)
    if vendor_match:
        vendor_name = vendor_match.group(1).strip()
    else:
        for line in lines[:3]:
            if not re.search(r'invoice|tax|bill|date', line, re.IGNORECASE) and len(line) > 3:
                vendor_name = line.strip()
                break

    # 4. Dates
    inv_date = ""
    date_match = re.search(r'(?:Invoice\s*Date|Date)\s*[:\-]?\s*([0-9]{1,4}[\/\-\.][A-Za-z0-9]+[\/\-\.][0-9]{2,4})', text, re.IGNORECASE)
    if date_match:
        inv_date = date_match.group(1).strip()

    due_date = None
    due_match = re.search(r'(?:Due\s*Date|Payment\s*Due)\s*[:\-]?\s*([0-9]{1,4}[\/\-\.][A-Za-z0-9]+[\/\-\.][0-9]{2,4})', text, re.IGNORECASE)
    if due_match:
        due_date = due_match.group(1).strip()

    # 5. Financial totals
    subtotal = 0.0
    sub_match = re.search(r'(?:Subtotal|Sub\s*Total|Net\s*Amount)\s*[:\-]?\s*(?:₹|\$|€|£|INR)?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)', text, re.IGNORECASE)
    if sub_match:
        subtotal = float(sub_match.group(1).replace(",", ""))

    # Tax breakdown
    taxes_breakdown = []
    cgst_val = None
    sgst_val = None
    cgst_match = re.search(r'CGST(?:\s*\([^\)]+\))?\s*[:\-]?\s*(?:₹|\$|€|£|INR)?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)', text, re.IGNORECASE)
    sgst_match = re.search(r'SGST(?:\s*\([^\)]+\))?\s*[:\-]?\s*(?:₹|\$|€|£|INR)?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)', text, re.IGNORECASE)
    igst_match = re.search(r'IGST(?:\s*\([^\)]+\))?\s*[:\-]?\s*(?:₹|\$|€|£|INR)?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)', text, re.IGNORECASE)
    
    total_tax = 0.0
    if cgst_match:
        cgst_val = float(cgst_match.group(1).replace(",", ""))
        taxes_breakdown.append({"tax_type": "CGST", "amount": cgst_val})
        total_tax += cgst_val
    if sgst_match:
        sgst_val = float(sgst_match.group(1).replace(",", ""))
        taxes_breakdown.append({"tax_type": "SGST", "amount": sgst_val})
        total_tax += sgst_val
    if igst_match:
        igst_amt = float(igst_match.group(1).replace(",", ""))
        taxes_breakdown.append({"tax_type": "IGST", "amount": igst_amt})
        total_tax += igst_amt

    if total_tax == 0.0:
        tax_match = re.search(r'(?:Total\s*Tax|Tax|VAT|GST)\s*(?:Amount)?\s*[:\-]?\s*(?:₹|\$|€|£|INR)?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)', text, re.IGNORECASE)
        if tax_match:
            total_tax = float(tax_match.group(1).replace(",", ""))

    # Check explicitly for Grand Total / Total line (anchored per line to avoid Subtotal / Total Tax)
    tot_match = re.search(r'^\s*(?:Grand\s*Total|Total\s*Amount|Final\s*Total|Total\s*Due|Total)\s*[:\-]?\s*(?:₹|\$|€|£|INR)?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)', text, re.IGNORECASE | re.MULTILINE)
    if tot_match:
        total = float(tot_match.group(1).replace(",", ""))
    elif subtotal > 0:
        total = round(subtotal + total_tax, 2)
    else:
        total = 0.0

    # 6. Line items
    line_items = []
    # Pattern 1: e.g. "1. Item Name | Qty: 2 | Price: 1500.00 | Amount: 3000.00"
    pipe_items = re.findall(r'(?:[0-9]+[\.\)]\s*)?([^|\n\r]+?)\s*\|\s*(?:Qty|Quantity)\s*[:\-]?\s*([0-9\.]+)\s*\|\s*(?:Price|Unit\s*Price)\s*[:\-]?\s*(?:₹|\$|€|£|INR)?\s*([0-9\.]+)\s*\|\s*(?:Amount|Total)\s*[:\-]?\s*(?:₹|\$|€|£|INR)?\s*([0-9\.]+)', text, re.IGNORECASE)
    for desc, q, p, a in pipe_items:
        line_items.append({
            "description": desc.strip(),
            "quantity": float(q),
            "price": float(p),
            "amount": float(a)
        })

    # Pattern 2: line containing description followed by numeric qty, price, total
    if not line_items:
        for line in lines:
            if re.search(r'total|subtotal|tax|date|invoice|due|buyer|vendor', line, re.IGNORECASE):
                continue
            m = re.match(r'(?:[0-9]+[\.\)]\s*)?([A-Za-z0-9\s\-_&,]+?)\s+([0-9]+(?:\.[0-9]+)?)\s+(?:₹|\$|€|£)?([0-9]+(?:\.[0-9]+)?)\s+(?:₹|\$|€|£)?([0-9]+(?:\.[0-9]+)?)$', line.strip())
            if m:
                desc, q, p, a = m.groups()
                line_items.append({
                    "description": desc.strip(),
                    "quantity": float(q),
                    "price": float(p),
                    "amount": float(a)
                })

    return {
        "invoice_number": invoice_number,
        "invoice_date": inv_date,
        "vendor_name": vendor_name,
        "due_date": due_date,
        "currency": currency,
        "line_items": line_items,
        "subtotal": round(subtotal, 2),
        "tax": round(total_tax, 2),
        "cgst": round(cgst_val, 2) if cgst_val is not None else None,
        "sgst": round(sgst_val, 2) if sgst_val is not None else None,
        "taxes_breakdown": taxes_breakdown if taxes_breakdown else None,
        "total": round(total, 2)
    }

def parse_deterministic_delivery_note(text: str) -> Dict[str, Any]:
    """Extracts structured delivery note fields from text."""
    dn_match = re.search(r'(?:Delivery\s*Note\s*(?:ID|No\.?|#)|DN-?)\s*[:#\-]?\s*([A-Za-z0-9\-_/]+)', text, re.IGNORECASE)
    delivery_note_id = dn_match.group(1).strip() if dn_match else ""

    date_match = re.search(r'(?:Delivery\s*Date|Date)\s*[:\-]?\s*([0-9]{1,4}[\/\-\.][A-Za-z0-9]+[\/\-\.][0-9]{2,4})', text, re.IGNORECASE)
    del_date = date_match.group(1).strip() if date_match else ""

    sender = ""
    sender_match = re.search(r'(?:Sender|From)\s*[:\-]\s*([^\n\r,]+)', text, re.IGNORECASE)
    if sender_match:
        sender = sender_match.group(1).strip()

    recipient = ""
    rec_match = re.search(r'(?:Recipient|Deliver\s*To|To)\s*[:\-]\s*([^\n\r,]+)', text, re.IGNORECASE)
    if rec_match:
        recipient = rec_match.group(1).strip()

    po_match = re.search(r'(?:PO\s*(?:Number|No\.?|#)|Purchase\s*Order)\s*[:#\-]?\s*([A-Za-z0-9\-_/]+)', text, re.IGNORECASE)
    po_number = po_match.group(1).strip() if po_match else None

    carrier_match = re.search(r'(?:Carrier|Courier|Transport)\s*[:\-]\s*([^\n\r,]+)', text, re.IGNORECASE)
    carrier = carrier_match.group(1).strip() if carrier_match else None

    rec_by_match = re.search(r'(?:Received\s*By|Signature)\s*[:\-]\s*([^\n\r,]+)', text, re.IGNORECASE)
    received_by = rec_by_match.group(1).strip() if rec_by_match else None

    items = []
    pipe_items = re.findall(r'(?:[0-9]+[\.\)]\s*)?([^|\n\r]+?)\s*\|\s*(?:Qty|Quantity)\s*[:\-]?\s*([0-9\.]+)\s*(?:\|\s*(?:Unit)\s*[:\-]?\s*([A-Za-z]+))?', text, re.IGNORECASE)
    for desc, q, unit in pipe_items:
        items.append({
            "description": desc.strip(),
            "quantity": float(q),
            "unit": unit.strip() if unit else "units"
        })

    return {
        "delivery_note_id": delivery_note_id,
        "delivery_date": del_date,
        "sender_name": sender,
        "recipient_name": recipient,
        "po_number": po_number,
        "items": items,
        "carrier_name": carrier,
        "received_by": received_by
    }

def parse_deterministic_contract(text: str) -> Dict[str, Any]:
    """Extracts structured contract fields from text."""
    contract_match = re.search(r'(?:Contract\s*(?:ID|No\.?|#)|Agreement\s*#)\s*[:#\-]?\s*([A-Za-z0-9\-_/]+)', text, re.IGNORECASE)
    contract_id = contract_match.group(1).strip() if contract_match else ""

    date_match = re.search(r'(?:Contract\s*Date|Date)\s*[:\-]?\s*([0-9]{1,4}[\/\-\.][A-Za-z0-9]+[\/\-\.][0-9]{2,4})', text, re.IGNORECASE)
    c_date = date_match.group(1).strip() if date_match else ""

    eff_match = re.search(r'(?:Effective\s*Date)\s*[:\-]?\s*([0-9]{1,4}[\/\-\.][A-Za-z0-9]+[\/\-\.][0-9]{2,4})', text, re.IGNORECASE)
    eff_date = eff_match.group(1).strip() if eff_match else c_date

    exp_match = re.search(r'(?:Expiration\s*Date|Termination\s*Date)\s*[:\-]?\s*([0-9]{1,4}[\/\-\.][A-Za-z0-9]+[\/\-\.][0-9]{2,4})', text, re.IGNORECASE)
    exp_date = exp_match.group(1).strip() if exp_match else None

    amt_match = re.search(r'(?:Contract\s*Amount|Value|Consideration)\s*[:\-]?\s*(?:₹|\$|€|£|INR)?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)', text, re.IGNORECASE)
    contract_amount = float(amt_match.group(1).replace(",", "")) if amt_match else None

    parties = []
    p_matches = re.findall(r'(?:Party\s*[0-9]+|Between)\s*[:\-]?\s*([^\n\r,]+)(?:\s*\((Client|Vendor|Contractor|Provider|Customer)\))?', text, re.IGNORECASE)
    for p_name, p_role in p_matches:
        parties.append({
            "name": p_name.strip(),
            "role": p_role.strip() if p_role else "Party"
        })

    clauses = []
    c_matches = re.findall(r'(?:Section\s*[0-9]+(?:\.[0-9]+)?|Clause\s*[0-9]+)\s*[:\-]?\s*([^\n\r]+)', text, re.IGNORECASE)
    for cl in c_matches:
        clauses.append(cl.strip())

    return {
        "contract_id": contract_id,
        "contract_date": c_date,
        "effective_date": eff_date,
        "expiration_date": exp_date,
        "contract_amount": contract_amount,
        "contract_type": "Agreement",
        "parties": parties,
        "key_clauses": clauses
    }

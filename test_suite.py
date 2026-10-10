import unittest
import io
import json
from fastapi.testclient import TestClient

from app.main import app
from app.models import InvoiceSchema, DeliveryNoteSchema, ContractSchema, ExtractionResponse
from app.extractor import get_mock_extraction, classify_by_filename, run_document_extraction, classify_by_content
from app.database import get_document_by_id, get_all_documents, save_document

client = TestClient(app)

SAMPLE_BLUEPEAK_INVOICE = b"""
INVOICE
Invoice Number: BP-INV-2026-1048
Invoice Date: 08-Oct-2026
Due Date: 07-Nov-2026
Vendor: BluePeak Office Supplies Pvt. Ltd.
Buyer: Global Tech Solutions Ltd.
Currency: INR

Line Items:
1. Ergonomic Mesh Chair | Qty: 2 | Price: 1500.00 | Amount: 3000.00
2. Wireless Keyboard & Mouse Combo | Qty: 3 | Price: 350.00 | Amount: 1050.00
3. Desk Organizer Tray | Qty: 4 | Price: 90.00 | Amount: 360.00

Subtotal: 4410.00
CGST (9%): 329.40
SGST (9%): 329.40
Total: 5068.80
"""

class TestDocuExtractComprehensive(unittest.TestCase):

    def test_01_classification_standard_invoice(self):
        self.assertEqual(classify_by_filename("vendor_invoice_101.pdf"), "Invoice")

    def test_02_classification_standard_delivery(self):
        self.assertEqual(classify_by_filename("goods_delivery_note_04.png"), "Delivery Note")

    def test_03_classification_standard_contract(self):
        self.assertEqual(classify_by_filename("master_services_agreement_2026.pdf"), "Contract")

    def test_04_classification_unknown_type(self):
        self.assertEqual(classify_by_filename("unrelated_photo_wallpaper.jpg"), "Unknown")

    def test_05_mock_standard_invoice_schema(self):
        res = get_mock_extraction("invoice_standard.pdf")
        self.assertEqual(res.doc_type, "Invoice")
        self.assertFalse(res.review_required)
        self.assertGreaterEqual(res.confidence, 0.90)
        schema = InvoiceSchema(**res.extracted_data)
        self.assertEqual(schema.invoice_number, "INV-2026-9084")
        self.assertEqual(schema.total, 1287.0)
        self.assertEqual(len(schema.line_items), 3)

    def test_06_mock_standard_delivery_note_schema(self):
        res = get_mock_extraction("delivery_note_standard.pdf")
        self.assertEqual(res.doc_type, "Delivery Note")
        self.assertFalse(res.review_required)
        self.assertGreaterEqual(res.confidence, 0.90)
        schema = DeliveryNoteSchema(**res.extracted_data)
        self.assertEqual(schema.delivery_note_id, "DN-88402")
        self.assertEqual(schema.received_by, "J. Robertson")

    def test_07_mock_standard_contract_schema(self):
        res = get_mock_extraction("contract_standard.pdf")
        self.assertEqual(res.doc_type, "Contract")
        self.assertFalse(res.review_required)
        self.assertGreaterEqual(res.confidence, 0.90)
        schema = ContractSchema(**res.extracted_data)
        self.assertEqual(schema.contract_id, "AGR-2026-0042")
        self.assertEqual(len(schema.parties), 2)

    def test_08_blurry_invoice_handling(self):
        res = get_mock_extraction("invoice_blurry_low_quality.jpg")
        self.assertEqual(res.doc_type, "Invoice")
        self.assertTrue(res.review_required)
        self.assertLess(res.confidence, 0.75)
        self.assertTrue(any("blurry" in r.lower() for r in res.review_reasons))

    def test_09_unusual_handwritten_receipt(self):
        res = get_mock_extraction("unusual_handwritten_receipt.jpg")
        self.assertEqual(res.doc_type, "Invoice")
        self.assertTrue(res.review_required)
        self.assertLess(res.confidence, 0.75)
        schema = InvoiceSchema(**res.extracted_data)
        self.assertEqual(schema.invoice_number, "REC-994A")

    def test_10_unknown_unsupported_document(self):
        res = get_mock_extraction("unknown_unsupported.pdf")
        self.assertEqual(res.doc_type, "Unknown")
        self.assertTrue(res.review_required)
        self.assertEqual(res.extracted_data, {})
        self.assertLess(res.confidence, 0.30)

    def test_11_content_fallback_invoice_with_contract_name(self):
        raw_bytes = b"Invoice Number: INV-9901\nVendor: Apex Tools\nSubtotal: 500.00\nTax: 50.00\nTotal: 550.00"
        res = run_document_extraction(None, "contract_agreement.pdf", "application/pdf", raw_bytes)
        self.assertEqual(res.doc_type, "Invoice")
        self.assertTrue(res.review_required)

    def test_12_content_fallback_delivery_with_invoice_name(self):
        raw_bytes = b"Delivery Note ID: DN-101\nReceived by: John Doe\nGoods Received: 50 units\nPurchase Order: PO-99"
        res = run_document_extraction(None, "invoice_bill.pdf", "application/pdf", raw_bytes)
        self.assertEqual(res.doc_type, "Delivery Note")
        self.assertTrue(res.review_required)

    def test_13_api_get_root_ui(self):
        res = client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/html", res.headers.get("content-type", ""))

    def test_14_api_list_documents(self):
        res = client.get("/api/documents")
        self.assertEqual(res.status_code, 200)
        docs = res.json()
        self.assertIsInstance(docs, list)
        self.assertGreaterEqual(len(docs), 6)

    def test_15_api_upload_mock_invoice(self):
        file_content = b"%PDF-1.4 Mock Invoice Content"
        res = client.post(
            "/api/extract",
            files={"file": ("invoice_standard.pdf", io.BytesIO(file_content), "application/pdf")}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["doc_type"], "Invoice")

    def test_16_api_reject_unsupported_file_extension(self):
        file_content = b"Mock Word Document"
        res = client.post(
            "/api/extract",
            files={"file": ("vendor_document.docx", io.BytesIO(file_content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        )
        self.assertEqual(res.status_code, 415)

    def test_17_api_reject_empty_file(self):
        empty_content = b""
        res = client.post(
            "/api/extract",
            files={"file": ("empty_invoice.pdf", io.BytesIO(empty_content), "application/pdf")}
        )
        self.assertEqual(res.status_code, 422)

    def test_18_api_reject_oversized_file(self):
        oversized = b"x" * (51 * 1024 * 1024)
        res = client.post(
            "/api/extract",
            files={"file": ("huge_invoice.pdf", io.BytesIO(oversized), "application/pdf")}
        )
        self.assertEqual(res.status_code, 413)

    def test_19_api_document_status_update_and_persistence(self):
        docs = get_all_documents()
        doc_id = docs[0].id
        orig_data = docs[0].extracted_data
        updated_data = dict(orig_data)
        updated_data["vendor_name"] = "Verified Corporate Vendor Ltd."
        
        res = client.post(f"/api/documents/{doc_id}/verify", json=updated_data)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "Verified")
        
        # Verify persistence across database lookup
        persisted = get_document_by_id(doc_id)
        self.assertIsNotNone(persisted)
        self.assertEqual(persisted.status, "Verified")
        self.assertEqual(persisted.extracted_data["vendor_name"], "Verified Corporate Vendor Ltd.")

    def test_20_user_fixture_bluepeak_invoice_extraction(self):
        """Validates exact extraction on the user's test invoice without canned mock data substitution."""
        res = run_document_extraction(
            api_key=None,  # Tests deterministic parser fallback
            filename="Vendor_Bill_BluePeak.pdf",
            mime_type="application/pdf",
            file_bytes=SAMPLE_BLUEPEAK_INVOICE
        )
        self.assertEqual(res.doc_type, "Invoice")
        data = res.extracted_data
        
        # Check expected information from the specification
        self.assertEqual(data["invoice_number"], "BP-INV-2026-1048")
        self.assertEqual(data["vendor_name"], "BluePeak Office Supplies Pvt. Ltd.")
        self.assertEqual(data["currency"], "INR")
        self.assertEqual(len(data["line_items"]), 3)
        self.assertEqual(data["line_items"][0]["description"], "Ergonomic Mesh Chair")
        self.assertEqual(data["line_items"][0]["quantity"], 2.0)
        self.assertEqual(data["line_items"][0]["price"], 1500.0)
        self.assertEqual(data["line_items"][0]["amount"], 3000.0)
        self.assertEqual(data["subtotal"], 4410.0)
        self.assertEqual(data["total"], 5068.80)

    def test_21_health_check_endpoint(self):
        res = client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["database"], "sqlite_ready")

    def test_22_invoice_nsm_26_2087_inr_tax_breakdown(self):
        """Test the NSM-26-2087 invoice: currency INR, CGST 385.20, SGST 385.20, total tax 770.40, total 5,540.40."""
        nsm_content = b"""
INVOICE
Invoice No: NSM-26-2087
Date: 12-Aug-2026
Vendor: NSM Industrial Solutions Ltd.
Currency: INR

Line Items:
1. Precision Stainless Bearing Unit | Qty: 4 | Price: 1042.50 | Amount: 4170.00
2. High-temp Flange Gasket Set | Qty: 2 | Price: 300.00 | Amount: 600.00

Subtotal: 4770.00
CGST (6%): 385.20
SGST (6%): 385.20
Total Tax: 770.40
Grand Total: 5,540.40
"""
        res = run_document_extraction(
            api_key=None,
            filename="NSM_Invoice_2087.pdf",
            mime_type="application/pdf",
            file_bytes=nsm_content
        )
        self.assertEqual(res.doc_type, "Invoice")
        self.assertEqual(res.engine_used, "Local Parser")
        data = res.extracted_data
        
        self.assertEqual(data["invoice_number"], "NSM-26-2087")
        self.assertEqual(data["currency"], "INR")
        self.assertEqual(data["cgst"], 385.20)
        self.assertEqual(data["sgst"], 385.20)
        self.assertEqual(data["tax"], 770.40)
        self.assertEqual(round(data["cgst"] + data["sgst"], 2), data["tax"])
        self.assertEqual(data["subtotal"], 4770.00)
        self.assertEqual(data["total"], 5540.40)
        self.assertEqual(len(data["line_items"]), 2)

    def test_23_invoice_usd_dynamic_currency(self):
        """Test a USD invoice to confirm dynamic currency extraction and line items."""
        usd_content = b"""
INVOICE
Invoice Number: US-9941
Invoice Date: 2026-09-01
Vendor: Apex US Technologies
Currency: USD

Line Items:
1. Cloud Server Hosting (Standard) | Qty: 1 | Price: 250.00 | Amount: 250.00

Subtotal: $250.00
Tax: $25.00
Total: $275.00
"""
        res = run_document_extraction(
            api_key=None,
            filename="Apex_Hosting_Bill.pdf",
            mime_type="application/pdf",
            file_bytes=usd_content
        )
        self.assertEqual(res.doc_type, "Invoice")
        self.assertEqual(res.engine_used, "Local Parser")
        data = res.extracted_data
        self.assertEqual(data["currency"], "USD")
        self.assertEqual(data["total"], 275.00)
        self.assertIsNone(data.get("cgst"))
        self.assertIsNone(data.get("sgst"))


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDocuExtractComprehensive)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    exit(not result.wasSuccessful())

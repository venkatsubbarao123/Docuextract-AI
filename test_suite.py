import unittest
import io
import json
from fastapi.testclient import TestClient

from app.main import app, documents_db
from app.models import InvoiceSchema, DeliveryNoteSchema, ContractSchema, ExtractionResponse
from app.extractor import get_mock_extraction, classify_by_filename, run_gemini_extraction

client = TestClient(app)


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
        res = run_gemini_extraction("dummy_invalid_key", "contract_agreement.pdf", "application/pdf", raw_bytes)
        self.assertEqual(res.doc_type, "Invoice")
        self.assertTrue(res.review_required)

    def test_12_content_fallback_delivery_with_invoice_name(self):
        raw_bytes = b"Delivery Note ID: DN-101\nReceived by: John Doe\nGoods Received: 50 units\nPurchase Order: PO-99"
        res = run_gemini_extraction("dummy_invalid_key", "invoice_bill.pdf", "application/pdf", raw_bytes)
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

    def test_19_api_document_status_update(self):
        doc_id = documents_db[0].id
        res = client.post(f"/api/documents/{doc_id}/verify", json={"invoice_number": "INV-VERIFIED-101"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "Verified")


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDocuExtractComprehensive)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    exit(not result.wasSuccessful())

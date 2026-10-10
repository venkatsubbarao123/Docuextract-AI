import sys
import unittest
from app.extractor import get_mock_extraction, classify_by_filename
from app.models import InvoiceSchema, DeliveryNoteSchema, ContractSchema


class TestDocumentExtractor(unittest.TestCase):

    def test_classification_by_filename(self):
        self.assertEqual(classify_by_filename("my_invoice_2026.pdf"), "Invoice")
        self.assertEqual(classify_by_filename("delivery_note_88.png"), "Delivery Note")
        self.assertEqual(classify_by_filename("vendor_agreement_signed.pdf"), "Contract")
        self.assertEqual(classify_by_filename("random_image_vacation.jpg"), "Unknown")

    def test_standard_invoice_extraction(self):
        res = get_mock_extraction("invoice_standard.pdf")
        self.assertEqual(res.doc_type, "Invoice")
        self.assertEqual(res.status, "Pending")
        self.assertFalse(res.review_required)
        self.assertGreaterEqual(res.confidence, 0.95)
        
        # Verify schema validity
        data = InvoiceSchema(**res.extracted_data)
        self.assertEqual(data.invoice_number, "INV-2026-9084")
        self.assertEqual(data.vendor_name, "Apex Industrial Supplies Ltd.")
        self.assertEqual(len(data.line_items), 3)
        self.assertEqual(data.total, 1287.0)

    def test_standard_delivery_note_extraction(self):
        res = get_mock_extraction("delivery_note_standard.pdf")
        self.assertEqual(res.doc_type, "Delivery Note")
        self.assertFalse(res.review_required)
        
        # Verify schema validity
        data = DeliveryNoteSchema(**res.extracted_data)
        self.assertEqual(data.delivery_note_id, "DN-88402")
        self.assertEqual(data.sender_name, "Apex Industrial Supplies Ltd.")
        self.assertEqual(len(data.items), 3)

    def test_standard_contract_extraction(self):
        res = get_mock_extraction("contract_standard.pdf")
        self.assertEqual(res.doc_type, "Contract")
        self.assertFalse(res.review_required)
        
        # Verify schema validity
        data = ContractSchema(**res.extracted_data)
        self.assertEqual(data.contract_id, "AGR-2026-0042")
        self.assertEqual(len(data.parties), 2)
        self.assertEqual(data.parties[0].role, "Client")

    def test_blurry_invoice_rejection(self):
        res = get_mock_extraction("invoice_blurry_low_quality.jpg")
        self.assertEqual(res.doc_type, "Invoice")
        self.assertTrue(res.review_required)
        self.assertLess(res.confidence, 0.70)
        self.assertTrue(any("blurry" in reason.lower() for reason in res.review_reasons))
        
        # Check that it still returns structured data but with warning markers
        data = InvoiceSchema(**res.extracted_data)
        self.assertIn("[BLURRY]", data.invoice_number)

    def test_unknown_document_handling(self):
        res = get_mock_extraction("unknown_unsupported.pdf")
        self.assertEqual(res.doc_type, "Unknown")
        self.assertTrue(res.review_required)
        self.assertEqual(res.extracted_data, {})
        self.assertLess(res.confidence, 0.30)
        self.assertTrue(any("unsupported" in reason.lower() or "classified" in reason.lower() for reason in res.review_reasons))


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDocumentExtractor)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(not result.wasSuccessful())

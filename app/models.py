from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Union, Dict, Any

# Invoice Schemas
class InvoiceLineItem(BaseModel):
    description: str = Field(default="", description="Description of the item or service")
    quantity: float = Field(default=1.0, description="Quantity of items purchased")
    price: float = Field(default=0.0, description="Unit price of the item")
    amount: float = Field(default=0.0, description="Total amount for this line item (quantity * price)")
    tax_rate: Optional[float] = Field(default=None, description="Optional tax rate percentage (e.g., 18.0)")

class InvoiceTaxDetail(BaseModel):
    tax_type: str = Field(default="Tax", description="Type of tax (e.g. CGST, SGST, IGST, VAT)")
    rate: Optional[float] = Field(default=None, description="Tax rate percentage")
    amount: float = Field(default=0.0, description="Tax amount")

class InvoiceSchema(BaseModel):
    invoice_number: str = Field(default="", description="The unique identification number of the invoice")
    invoice_date: str = Field(default="", description="Date when the invoice was issued (YYYY-MM-DD or raw string)")
    vendor_name: str = Field(default="", description="Name of the company or person issuing the invoice")
    buyer_name: Optional[str] = Field(default=None, description="Name of the customer or buyer organization")
    due_date: Optional[str] = Field(default=None, description="Date by which the invoice must be paid")
    po_number: Optional[str] = Field(default=None, description="Purchase order reference number")
    currency: str = Field(default="USD", description="Currency symbol or code (e.g. INR, USD, EUR, GBP)")
    line_items: List[InvoiceLineItem] = Field(default_factory=list, description="List of individual items billed")
    subtotal: float = Field(default=0.0, description="Subtotal amount before tax")
    tax: float = Field(default=0.0, description="Total tax amount billed")
    cgst: Optional[float] = Field(default=None, description="Central GST amount if applicable")
    sgst: Optional[float] = Field(default=None, description="State GST amount if applicable")
    taxes_breakdown: Optional[List[InvoiceTaxDetail]] = Field(default=None, description="Optional breakdown of tax components like CGST/SGST")
    total: float = Field(default=0.0, description="Grand total amount due")

# Delivery Note Schemas
class DeliveryNoteLineItem(BaseModel):
    description: str = Field(default="", description="Description of the goods delivered")
    quantity: float = Field(default=1.0, description="Quantity delivered")
    unit: str = Field(default="units", description="Unit of measurement (e.g., pcs, kg, boxes)")

class DeliveryNoteSchema(BaseModel):
    delivery_note_id: str = Field(default="", description="The identification number of the delivery note")
    delivery_date: str = Field(default="", description="Date when the delivery was made")
    recipient_name: str = Field(default="", description="Name of the person or organization receiving the delivery")
    sender_name: str = Field(default="", description="Name of the person or organization sending the delivery")
    po_number: Optional[str] = Field(default=None, description="Purchase order reference number")
    items: List[DeliveryNoteLineItem] = Field(default_factory=list, description="List of items delivered")
    carrier_name: Optional[str] = Field(default=None, description="Name of the delivery company or carrier")
    received_by: Optional[str] = Field(default=None, description="Signature or name of the person who acknowledged delivery")

# Contract Schemas
class ContractParty(BaseModel):
    name: str = Field(default="", description="Name of the legal entity or person")
    role: str = Field(default="Party", description="Role in the contract (e.g., Client, Vendor, Contractor)")

class ContractSchema(BaseModel):
    contract_id: str = Field(default="", description="The identification number or title of the agreement")
    contract_date: str = Field(default="", description="Date when the contract was signed or executed")
    parties: List[ContractParty] = Field(default_factory=list, description="The legal entities or parties involved in the contract")
    effective_date: str = Field(default="", description="The date when the contract becomes active")
    expiration_date: Optional[str] = Field(default=None, description="The date when the contract terminates")
    contract_amount: Optional[float] = Field(default=None, description="Total monetary value of the contract, if specified")
    currency: Optional[str] = Field(default=None, description="Contract value currency (e.g. INR, USD, EUR)")
    contract_type: str = Field(default="Agreement", description="Type of agreement (e.g., NDA, MSA, SLA)")
    key_clauses: List[str] = Field(default_factory=list, description="Important clauses extracted")

# Unified Extraction Response
class ExtractionResponse(BaseModel):
    id: str = Field(description="Unique internal ID for tracking the document")
    filename: str = Field(description="Name of the uploaded file")
    doc_type: str = Field(description="Classified document type: 'Invoice', 'Delivery Note', 'Contract', or 'Unknown'")
    extracted_data: Dict[str, Any] = Field(default_factory=dict, description="The key-value pairs matching the respective schema")
    confidence: float = Field(description="Overall extraction confidence score (0.0 to 1.0)")
    classification_confidence: float = Field(default=0.90, description="Confidence in document classification (0.0 to 1.0)")
    review_required: bool = Field(description="Whether a human operator needs to review the extraction")
    review_reasons: List[str] = Field(default_factory=list, description="Reasons why review is flagged")
    status: str = Field(default="Pending", description="Processing status: 'Pending' or 'Verified'")
    engine_used: str = Field(default="Local Parser", description="The engine that executed the extraction ('Gemini AI', 'Local Parser', or 'Mock Mode')")

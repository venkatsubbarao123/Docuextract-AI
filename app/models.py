from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any

# Invoice Schemas
class InvoiceLineItem(BaseModel):
    description: str = Field(description="Description of the item or service")
    quantity: float = Field(description="Quantity of items purchased")
    price: float = Field(description="Unit price of the item")
    amount: float = Field(description="Total amount for this line item (quantity * price)")

class InvoiceSchema(BaseModel):
    invoice_number: str = Field(description="The unique identification number of the invoice")
    invoice_date: str = Field(description="Date when the invoice was issued (YYYY-MM-DD or raw string)")
    vendor_name: str = Field(description="Name of the company or person issuing the invoice")
    line_items: List[InvoiceLineItem] = Field(default=[], description="List of individual items billed")
    subtotal: float = Field(description="Subtotal amount before tax")
    tax: float = Field(description="Tax amount billed")
    total: float = Field(description="Total amount due")
    due_date: Optional[str] = Field(default=None, description="Date by which the invoice must be paid")

# Delivery Note Schemas
class DeliveryNoteLineItem(BaseModel):
    description: str = Field(description="Description of the goods delivered")
    quantity: float = Field(description="Quantity delivered")
    unit: str = Field(default="units", description="Unit of measurement (e.g., pcs, kg, boxes)")

class DeliveryNoteSchema(BaseModel):
    delivery_note_id: str = Field(description="The identification number of the delivery note")
    delivery_date: str = Field(description="Date when the delivery was made")
    recipient_name: str = Field(description="Name of the person or organization receiving the delivery")
    sender_name: str = Field(description="Name of the person or organization sending the delivery")
    po_number: Optional[str] = Field(default=None, description="Purchase order reference number")
    items: List[DeliveryNoteLineItem] = Field(default=[], description="List of items delivered")
    carrier_name: Optional[str] = Field(default=None, description="Name of the delivery company or carrier")
    received_by: Optional[str] = Field(default=None, description="Signature or name of the person who acknowledged delivery")

# Contract Schemas
class ContractParty(BaseModel):
    name: str = Field(description="Name of the legal entity or person")
    role: str = Field(description="Role in the contract (e.g., Client, Vendor, Employer, Employee)")

class ContractSchema(BaseModel):
    contract_id: str = Field(description="The identification number or title of the agreement")
    contract_date: str = Field(description="Date when the contract was signed or executed")
    parties: List[ContractParty] = Field(default=[], description="The legal entities or parties involved in the contract")
    effective_date: str = Field(description="The date when the contract becomes active")
    expiration_date: Optional[str] = Field(default=None, description="The date when the contract terminates")
    contract_amount: Optional[float] = Field(default=None, description="Total monetary value of the contract, if specified")
    contract_type: str = Field(description="Type of agreement (e.g., NDA, MSA, SLA, Employment)")
    key_clauses: List[str] = Field(default=[], description="Important clauses extracted (e.g., termination notice, indemnity)")

# Unified Extraction Response
class ExtractionResponse(BaseModel):
    id: str = Field(description="Unique internal ID for tracking the document")
    filename: str = Field(description="Name of the uploaded file")
    doc_type: str = Field(description="Classified document type: 'Invoice', 'Delivery Note', 'Contract', or 'Unknown'")
    extracted_data: Dict[str, Any] = Field(default={}, description="The key-value pairs matching the respective schema")
    confidence: float = Field(description="Overall extraction confidence score (0.0 to 1.0)")
    review_required: bool = Field(description="Whether a human operator needs to review the extraction")
    review_reasons: List[str] = Field(default=[], description="Reasons why review is flagged (e.g., low confidence, missing totals, unreadable scans)")
    status: str = Field(default="Pending", description="Processing status: 'Pending' or 'Verified'")

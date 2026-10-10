
# DocuExtract AI

### Intelligent Document Extraction & Structuring Agent

DocuExtract AI is an AI-powered document processing application that automatically analyzes vendor documents in PDF and image formats, identifies the document type, and converts unstructured document content into validated structured JSON.

The system is designed to work with different document layouts and provides confidence scoring, low-quality document handling, and a human-in-the-loop verification workflow for uncertain extractions.

---

## Overview

Vendor documents such as invoices, delivery notes, and contracts often have different layouts, structures, and levels of document quality.

DocuExtract AI provides an automated pipeline to:

1. Upload a PDF or image document.
2. Analyze the document content.
3. Identify its document type.
4. Extract relevant information.
5. Convert the information into a structured JSON schema.
6. Validate the extracted data.
7. Calculate an extraction confidence score.
8. Flag uncertain documents for human review.
9. Allow users to correct and verify extracted information.

---

## ✨ Features

- 📄 PDF and image document processing
- 🔍 Automatic document classification
- 🤖 Gemini multimodal AI extraction
- 📦 Type-specific structured JSON output
- ✅ Pydantic schema validation
- 📊 Extraction confidence scoring
- ⚠️ Low-confidence detection
- 👨‍💼 Human-in-the-loop verification
- ✏️ Editable extracted fields
- 📋 Raw JSON viewer
- 🔄 Intelligent fallback processing
- 🛡️ File validation and error handling
- 📑 Invoice, Delivery Note and Contract support
- 🌐 FastAPI REST API
- 🎨 Interactive web dashboard
- 🧪 Automated unit and integration testing

---

# Supported Document Types

## 1. Invoice

The invoice extraction schema includes:

- Invoice Number
- Invoice Date
- Vendor Name
- Line Items
- Quantity
- Unit Price
- Amount
- Subtotal
- Tax
- Total
- Due Date

### Example

```json
{
  "invoice_number": "INV-2026-9084",
  "invoice_date": "2026-08-15",
  "vendor_name": "Apex Industrial Supplies Ltd.",
  "line_items": [
    {
      "description": "Heavy-duty Hydraulic Cylinders (Model H-400)",
      "quantity": 2,
      "price": 450,
      "amount": 900
    },
    {
      "description": "Industrial Sealant Cartridges",
      "quantity": 10,
      "price": 18.5,
      "amount": 185
    }
  ],
  "subtotal": 1170,
  "tax": 117,
  "total": 1287,
  "due_date": "2026-09-15"
}
````

---

## 2. Delivery Note

The Delivery Note schema supports fields such as:

* Delivery Note ID
* Delivery Date
* Sender
* Recipient
* Purchase Order
* Items
* Carrier
* Received By

---

## 3. Contract

The Contract schema supports fields such as:

* Contract ID
* Contract Date
* Parties
* Effective Date
* Expiration Date
* Contract Amount
* Contract Type
* Key Clauses

---

# 🏗️ System Architecture

```text
                         USER
                           │
                           ▼
                ┌─────────────────────┐
                │   Web Dashboard     │
                │ PDF / Image Upload  │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │    FastAPI API      │
                │ File Validation     │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Document Classifier │
                └──────────┬──────────┘
                           │
                    ┌──────┴──────┐
                    │             │
                    ▼             ▼
             Gemini AI       Fallback Engine
             Multimodal            │
                    │              │
                    └──────┬───────┘
                           ▼
                ┌─────────────────────┐
                │ Structured JSON     │
                │ Schema Extraction   │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Pydantic Validation │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Confidence Engine   │
                └──────────┬──────────┘
                           │
                    ┌──────┴──────┐
                    │             │
                    ▼             ▼
             High Confidence   Low Confidence
                    │             │
                    ▼             ▼
                Verified      Human Review
                                  │
                                  ▼
                           User Correction
                                  │
                                  ▼
                              Verified
```

---

# 🔄 Processing Workflow

```text
Document Upload
      │
      ▼
File Validation
      │
      ▼
Document Classification
      │
      ├── Invoice
      ├── Delivery Note
      ├── Contract
      └── Unknown
      │
      ▼
Structured Data Extraction
      │
      ▼
Schema Validation
      │
      ▼
Confidence Evaluation
      │
      ├── High Confidence ──► Normal Processing
      │
      └── Low Confidence ──► Human Review
                                      │
                                      ▼
                                User Correction
                                      │
                                      ▼
                                   Verified
```

---

# 🤖 AI Processing

## Gemini Multimodal Engine

When a Gemini API key is configured, the application uses Gemini's multimodal capabilities to analyze PDF and image documents.

The AI pipeline performs:

1. Document understanding
2. Document classification
3. Field extraction
4. Structured JSON generation
5. Schema validation
6. Confidence evaluation
7. Review decision

Structured JSON output is generated according to the document-specific schema.

---

# 🔄 Fallback Processing

The application also includes a deterministic fallback mechanism.

If the Gemini API is unavailable, invalid, or not configured, the application can fall back to content-based processing.

The fallback mechanism:

* Inspects available document content.
* Detects document signatures.
* Determines the likely document type.
* Populates the corresponding schema where possible.
* Reduces confidence when extraction is uncertain.
* Routes uncertain documents for human review.

This prevents an external AI/API failure from causing the entire application to fail.

---

# ⚠️ Low-Quality Document Handling

Document quality can vary significantly in real-world scenarios.

DocuExtract AI is designed to handle cases such as:

* Blurry documents
* Low-quality scans
* Unusual layouts
* Handwritten or partially readable documents
* Missing fields
* Unknown document types

Instead of failing outright, the system extracts the information it can identify and provides a confidence score.

### Example

```json
{
  "doc_type": "Invoice",
  "confidence": 0.52,
  "review_required": true,
  "review_reasons": [
    "Blurry or smudged scan detected",
    "Required fields could not be reliably extracted",
    "Confidence below review threshold"
  ]
}
```

This allows uncertain documents to continue through the workflow instead of causing an application failure.

---

# 📊 Confidence & Review System

Each extraction receives a confidence score based on extraction quality and consistency signals.

The system considers factors such as:

* Field completeness
* Missing values
* Document quality
* Extraction consistency
* Financial calculation consistency
* Required schema fields

Documents below the configured review threshold are automatically flagged for manual verification.

> The confidence score is an operational extraction-quality score and should not be interpreted as a calibrated statistical probability.

---

# 👨‍💼 Human-in-the-Loop Verification

Low-confidence documents are placed into a review workflow.

The reviewer can:

* Inspect extracted fields
* Edit incorrect values
* Add line items
* Remove incorrect line items
* Review the raw JSON
* Correct extracted information
* Approve and verify the document

After successful verification, the document status changes to:

```text
Status: Verified
Review Required: No
```

This provides a practical human-in-the-loop workflow for handling uncertain AI extraction results.

---

# 🛡️ File Validation

The backend validates uploaded files before processing.

Supported formats:

```text
PDF
PNG
JPG
JPEG
WEBP
```

The application also validates:

* File extension
* Empty files
* Maximum file size
* Unsupported formats
* Invalid extraction requests

This prevents unsupported or invalid files from entering the processing pipeline.

---

# 🧪 Testing

The project includes automated unit and integration tests.

Run:

```bash
python test_suite.py
```

### Current Test Result

```text
Ran 19 tests

OK

19 Passed
0 Failed
0 Errors
```

The test suite covers:

* Document classification
* Invoice extraction
* Delivery Note extraction
* Contract extraction
* Unknown document handling
* Low-quality document handling
* Unusual document handling
* Content-based fallback classification
* API endpoints
* File type validation
* Empty file validation
* Oversized file validation
* Human verification workflow
* Schema validation

---

# 🛠️ Technology Stack

## Backend

* Python
* FastAPI
* Uvicorn
* Pydantic

## AI

* Google Gemini Multimodal API
* Structured JSON extraction

## Frontend

* HTML5
* CSS3
* JavaScript
* Tailwind CSS

## Testing

* Python unittest
* FastAPI TestClient

## Deployment

* GitHub
* Render

---

# 📁 Project Structure

```text
Docuextract-AI/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   ├── extractor.py
│   │
│   └── static/
│       ├── index.html
│       ├── styles.css
│       └── app.js
│
├── requirements.txt
├── run.bat
├── test_extractor.py
├── test_suite.py
├── .gitignore
└── README.md
```

---

# 🚀 Getting Started

## 1. Clone the repository

```bash
git clone https://github.com/venkatsubbarao123/Docuextract-AI.git
```

## 2. Navigate to the project

```bash
cd Docuextract-AI
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Start the application

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8008
```

Open the application in your browser:

```text
http://127.0.0.1:8008
```

### Windows

You can also use:

```text
run.bat
```

---

# 🔐 API Key Configuration

The Gemini API key should never be committed to the repository.

For local development, configure:

```text
GEMINI_API_KEY=YOUR_API_KEY
```

The `.env` file should remain excluded through `.gitignore`.

For deployment, configure the API key using the hosting platform's environment variable settings.

---

# 🌐 Live Demo

### Application

[https://docuextract-ai-34gs.onrender.com](https://docuextract-ai-34gs.onrender.com)

### Source Code

[https://github.com/venkatsubbarao123/Docuextract-AI](https://github.com/venkatsubbarao123/Docuextract-AI)

---

# 📌 Design Assumptions

* Synthetic or mock vendor documents are used for demonstration.
* The supported document categories are Invoice, Delivery Note and Contract.
* Documents outside supported categories are classified as Unknown.
* Low-confidence extractions are routed for human review.
* The current assessment/demo version uses in-memory document storage.
* Production deployment can use persistent database and object storage infrastructure.

---

# 🔮 Future Improvements

Potential production improvements include:

* Dedicated OCR using Tesseract or PaddleOCR
* PostgreSQL persistence
* Persistent object storage
* Asynchronous document processing
* Batch folder processing
* Page-level confidence scoring
* Authentication and role-based access control
* Additional document types
* Advanced document layout analysis
* Document processing queues
* Production monitoring and logging

---

👨‍💻 Author

CH Venkata Subba Rao

**AI / ML | Python | FastAPI | NLP | Generative AI**

GitHub:
[https://github.com/venkatsubbarao123](https://github.com/venkatsubbarao123)


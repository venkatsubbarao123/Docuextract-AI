import sqlite3
import json
import os
from typing import List, Optional, Dict, Any
from .models import ExtractionResponse

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "documents.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                doc_type TEXT NOT NULL,
                extracted_data TEXT NOT NULL,
                confidence REAL NOT NULL,
                classification_confidence REAL NOT NULL DEFAULT 0.0,
                review_required INTEGER NOT NULL,
                review_reasons TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def save_document(doc: ExtractionResponse) -> None:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO documents 
            (id, filename, doc_type, extracted_data, confidence, classification_confidence, review_required, review_reasons, status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            doc.id,
            doc.filename,
            doc.doc_type,
            json.dumps(doc.extracted_data),
            doc.confidence,
            getattr(doc, "classification_confidence", doc.confidence),
            1 if doc.review_required else 0,
            json.dumps(doc.review_reasons),
            doc.status
        ))
        conn.commit()

def get_document_by_id(doc_id: str) -> Optional[ExtractionResponse]:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return ExtractionResponse(
            id=row["id"],
            filename=row["filename"],
            doc_type=row["doc_type"],
            extracted_data=json.loads(row["extracted_data"]),
            confidence=row["confidence"],
            classification_confidence=row["classification_confidence"],
            review_required=bool(row["review_required"]),
            review_reasons=json.loads(row["review_reasons"]),
            status=row["status"]
        )

def get_all_documents(
    doc_type: Optional[str] = None,
    status: Optional[str] = None,
    review_required: Optional[bool] = None,
    search: Optional[str] = None
) -> List[ExtractionResponse]:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = "SELECT * FROM documents ORDER BY updated_at DESC"
        cursor.execute(query)
        rows = cursor.fetchall()
        
        docs = []
        for row in rows:
            doc = ExtractionResponse(
                id=row["id"],
                filename=row["filename"],
                doc_type=row["doc_type"],
                extracted_data=json.loads(row["extracted_data"]),
                confidence=row["confidence"],
                classification_confidence=row["classification_confidence"],
                review_required=bool(row["review_required"]),
                review_reasons=json.loads(row["review_reasons"]),
                status=row["status"]
            )
            docs.append(doc)

    if doc_type:
        docs = [d for d in docs if d.doc_type.lower() == doc_type.lower()]
    if status:
        docs = [d for d in docs if d.status.lower() == status.lower()]
    if review_required is not None:
        docs = [d for d in docs if d.review_required == review_required]
    if search:
        s_lower = search.lower()
        docs = [d for d in docs if s_lower in d.filename.lower() or s_lower in d.doc_type.lower()]

    return docs

def get_stats_data() -> Dict[str, Any]:
    docs = get_all_documents()
    total = len(docs)
    needs_review = sum(1 for d in docs if d.review_required)
    verified = sum(1 for d in docs if d.status == "Verified")
    avg_conf = (sum(d.confidence for d in docs) / total) if total > 0 else 0.0
    type_counts = {"Invoice": 0, "Delivery Note": 0, "Contract": 0, "Unknown": 0}
    for d in docs:
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

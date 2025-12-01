"""CLI to ingest aviation PDFs into RAG with aviation metadata.

ALLOWED sources:
- Public MMELs and equivalent public documents.
- Public regulations and safety documents (FAA/EASA, advisory circulars).
- Human Factors handbooks.
- Company MEL, MOE, procedures, engineering memos, and reliability reports explicitly uploaded by the tenant.

FORBIDDEN:
- Proprietary OEM manuals: AMM, SRM, IPC, FCOM, TSM, WDM, system schematics, etc.
"""
import argparse
import os
from typing import List, Dict, Any

from ..rag_module import RAGPipeline


FORBIDDEN_PREFIXES = ("AMM", "SRM", "IPC", "FCOM", "TSM", "WDM")
FORBIDDEN_KEYWORDS = ("_AMM", "_SRM", "_IPC", "_FCOM", "_TSM", "_WDM")


def is_forbidden_filename(name: str) -> bool:
    upper = name.upper()
    if upper.startswith(FORBIDDEN_PREFIXES):
        return True
    return any(k in upper for k in FORBIDDEN_KEYWORDS)


def extract_text_from_pdf(path: str) -> str:
    # Minimal placeholder to avoid hard dependency on pypdf
    # In production, replace with proper PDF text extraction (e.g. pypdf).
    return f"[PDF content placeholder for {os.path.basename(path)}]"


def build_chunks(text: str, meta: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [{"content": text, **meta}]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_dir", type=str, help="Directory containing PDFs to ingest")
    parser.add_argument("--company", type=int, required=True, help="Company (tenant) ID")
    parser.add_argument("--aircraft", type=str, required=False, default="", help="Aircraft model hint")
    parser.add_argument("--ata", type=str, required=False, default="", help="ATA chapter hint")
    parser.add_argument("--doctype", type=str, required=False, default="MMEL", help="Document type (MMEL, MEL, MOE, REG, HF, COMPANY_PROC, RELIABILITY)")
    args = parser.parse_args()

    pipeline = RAGPipeline(collection="aerobrain_docs")

    for root, _, files in os.walk(args.pdf_dir):
        for fname in files:
            if not fname.lower().endswith(".pdf"):
                continue
            if is_forbidden_filename(fname):
                print(f"[SKIP] Forbidden-looking filename (possible OEM manual): {fname}")
                continue
            fpath = os.path.join(root, fname)
            text = extract_text_from_pdf(fpath)
            meta = {
                "company_id": args.company,
                "aircraft_model": args.aircraft,
                "ata_chapter": args.ata,
                "doc_type": args.doctype,
                "source_path": fpath,
                "doc_title": os.path.splitext(fname)[0],
            }
            chunks = build_chunks(text, meta)
            pipeline.ingest_document(chunks)
            print(f"[OK] Ingested {fname}")


if __name__ == "__main__":
    main()

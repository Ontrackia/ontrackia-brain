"""RAG module using ChromaDB for aviation documents."""
from typing import List, Dict, Any, Optional
import os
from pathlib import Path

import chromadb
from chromadb.config import Settings

# Initialize ChromaDB with persistent storage
DB_PATH = Path(__file__).parent.parent / "data" / "chromadb"
DB_PATH.mkdir(parents=True, exist_ok=True)

client = chromadb.PersistentClient(path=str(DB_PATH))

def get_or_create_collection(name: str = "aerobrain_docs"):
    """Get or create a ChromaDB collection."""
    return client.get_or_create_collection(
        name=name,
        metadata={"description": "Aviation documents for AeroEngineer AI Brain"}
    )


class RAGPipeline:
    """ChromaDB-based RAG for aviation documents."""
    
    def __init__(self, collection: str = "aerobrain_docs"):
        self.collection = get_or_create_collection(collection)
    
    def ingest_document(self, chunks: List[Dict[str, Any]]) -> None:
        """Ingest document chunks into ChromaDB."""
        if not chunks:
            return
        
        documents = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            content = chunk.get("content", "")
            if not content.strip():
                continue
                
            doc_id = f"{chunk.get('doc_title', 'doc')}_{chunk.get('aircraft_model', 'unknown')}_{i}"
            
            documents.append(content)
            metadatas.append({
                "company_id": str(chunk.get("company_id", 0)),
                "aircraft_model": chunk.get("aircraft_model", ""),
                "ata_chapter": chunk.get("ata_chapter", ""),
                "doc_type": chunk.get("doc_type", ""),
                "source_path": chunk.get("source_path", ""),
                "doc_title": chunk.get("doc_title", ""),
            })
            ids.append(doc_id)
        
        if documents:
            # Upsert to handle duplicates
            self.collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
    
    def query(
        self,
        question: str,
        company_id: Optional[int],
        aircraft_model: Optional[str],
        ata_chapter: Optional[str],
        top_k: int = 5
    ) -> Dict[str, Any]:
        """Query the vector store."""
        
        # Build where filter
        where_filter = None
        if aircraft_model:
            # Match aircraft model (case insensitive matching done via contains)
            aircraft_upper = aircraft_model.upper()
            where_filter = {"aircraft_model": {"$eq": aircraft_upper}}
        
        try:
            results = self.collection.query(
                query_texts=[question],
                n_results=top_k,
                where=where_filter if where_filter else None,
            )
        except Exception as e:
            print(f"[RAG] Query error: {e}")
            return {"fuentes": [], "confianza": 0.0}
        
        fuentes = []
        total_score = 0.0
        
        if results and results.get("documents") and results["documents"][0]:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
            distances = results["distances"][0] if results.get("distances") else [1.0] * len(docs)
            
            for doc, meta, dist in zip(docs, metas, distances):
                # ChromaDB returns L2 distance, convert to similarity score
                # Lower distance = higher similarity
                score = max(0, 1 - (dist / 2))
                total_score += score
                
                fuentes.append({
                    "content": doc,
                    "doc_title": meta.get("doc_title", "Unknown"),
                    "aircraft_model": meta.get("aircraft_model", ""),
                    "doc_type": meta.get("doc_type", ""),
                    "source_path": meta.get("source_path", ""),
                    "score": round(score, 3)
                })
        
        # Calculate average confidence
        confianza = (total_score / len(fuentes)) if fuentes else 0.0
        
        return {
            "fuentes": fuentes,
            "confianza": round(confianza, 3)
        }


def query_rag(
    question: str,
    company_id: Optional[int],
    aircraft_model: Optional[str],
    ata_chapter: Optional[str]
) -> Dict[str, Any]:
    """Entry point used by the agent."""
    pipeline = RAGPipeline(collection="aerobrain_docs")
    return pipeline.query(question, company_id, aircraft_model, ata_chapter, top_k=5)


def ingest_markdown_folder(folder_path: str, aircraft_model: str = "", company_id: int = 1) -> int:
    """Ingest all markdown files from a folder into RAG."""
    pipeline = RAGPipeline()
    count = 0
    
    folder = Path(folder_path)
    for md_file in folder.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
            
            # Determine aircraft from parent folder name if not specified
            detected_aircraft = aircraft_model
            parent_name = md_file.parent.name.upper()
            if not detected_aircraft:
                if "737MAX" in parent_name or "B737MAX" in parent_name:
                    detected_aircraft = "B737MAX"
                elif "737NG" in parent_name or "B737NG" in parent_name:
                    detected_aircraft = "B737NG"
                elif "767" in parent_name:
                    detected_aircraft = "B767"
                elif "777" in parent_name:
                    detected_aircraft = "B777"
                elif "787" in parent_name:
                    detected_aircraft = "B787"
                elif "COMMON" in parent_name:
                    detected_aircraft = "COMMON"
            
            # Determine doc type from filename
            filename = md_file.stem.lower()
            if "translator" in filename:
                doc_type = "TRANSLATOR"
            elif "few_shot" in filename:
                doc_type = "FEW_SHOT"
            elif "acronym" in filename:
                doc_type = "ACRONYMS"
            else:
                doc_type = "REFERENCE"
            
            chunks = [{
                "content": content,
                "company_id": company_id,
                "aircraft_model": detected_aircraft,
                "ata_chapter": "",
                "doc_type": doc_type,
                "source_path": str(md_file),
                "doc_title": md_file.stem,
            }]
            
            pipeline.ingest_document(chunks)
            count += 1
            print(f"[OK] Ingested: {md_file.name} -> {detected_aircraft}")
            
        except Exception as e:
            print(f"[ERROR] Failed to ingest {md_file}: {e}")
    
    return count
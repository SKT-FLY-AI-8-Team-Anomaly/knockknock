"""
RAG (Retrieval Augmented Generation) Core Module
Handles document embedding, storage, retrieval, and similarity search
"""

import uuid
from datetime import datetime
from typing import Any, Optional
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import json
import math


@dataclass
class RagDoc:
    """Document structure for RAG system"""
    id: str
    text: str
    embedding: list[float]
    metadata: Optional[dict[str, Any]] = None
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "RagDoc":
        return cls(**data)


class IRAGStore(ABC):
    """Interface for RAG document storage"""
    
    @abstractmethod
    async def get_rag_docs(self) -> list[RagDoc]:
        """Retrieve all stored documents"""
        pass
    
    @abstractmethod
    async def save_rag_docs(self, docs: list[RagDoc]) -> None:
        """Save documents to storage"""
        pass


class IEmbeddingService(ABC):
    """Interface for embedding service"""
    
    @abstractmethod
    async def create_embedding(self, input_text: str) -> list[float]:
        """Create embedding for text"""
        pass


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    if len(a) != len(b):
        return 0.0
    
    dot = sum(x * y for x, y in zip(a, b))
    a_norm = math.sqrt(sum(x ** 2 for x in a))
    b_norm = math.sqrt(sum(x ** 2 for x in b))
    
    if a_norm == 0 or b_norm == 0:
        return 0.0
    
    return dot / (a_norm * b_norm)


class RAGManager:
    """Manages document retrieval and augmented generation"""
    
    def __init__(
        self,
        store: IRAGStore,
        embedding_service: IEmbeddingService,
        top_k: int = 4
    ):
        self.store = store
        self.embedding_service = embedding_service
        self.top_k = top_k
    
    async def add_documents(
        self,
        texts: list[str],
        metadata: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Add new documents to the RAG database"""
        if not texts:
            raise ValueError("At least one text is required")
        
        existing = await self.store.get_rag_docs()
        
        for text in texts:
            embedding = await self.embedding_service.create_embedding(str(text))
            doc = RagDoc(
                id=str(uuid.uuid4()),
                text=str(text),
                embedding=embedding,
                metadata=metadata
            )
            existing.append(doc)
        
        await self.store.save_rag_docs(existing)
        return {"success": True, "count": len(texts)}
    
    async def retrieve_documents(self, query: str) -> list[RagDoc]:
        """Retrieve documents similar to the query"""
        docs = await self.store.get_rag_docs()
        
        if not docs:
            return []
        
        query_embedding = await self.embedding_service.create_embedding(query)
        
        # Calculate similarity scores
        scored_docs = [
            (doc, cosine_similarity(query_embedding, doc.embedding))
            for doc in docs
        ]
        
        # Sort by score and get top K
        ranked = sorted(scored_docs, key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in ranked[:self.top_k]]
    
    def format_context(self, docs: list[RagDoc]) -> str:
        """Format retrieved documents as context string"""
        if not docs:
            return ""
        
        return "\n\n".join(
            f"문서 {i + 1}:\n{doc.text}"
            for i, doc in enumerate(docs)
        )
    
    async def get_all_documents(self) -> list[RagDoc]:
        """Get all stored documents"""
        return await self.store.get_rag_docs()
    
    async def clear_documents(self) -> None:
        """Clear all documents"""
        await self.store.save_rag_docs([])
    
    def set_top_k(self, top_k: int) -> None:
        """Set the number of top documents to retrieve"""
        self.top_k = top_k

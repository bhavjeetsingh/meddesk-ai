"""
CareFirst Medical Center - Seed Script
Populates the vector store with clinic documents (Ollama + HuggingFace)
"""
import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings
from core.rag_engine import CareFirstRAG
from core.database import init_db, seed_data
from loguru import logger


async def seed_knowledge_base():
    """Seed the vector store with clinic documents"""
    settings = get_settings()
    rag = CareFirstRAG(settings)

    logger.info("Initializing RAG engine...")
    await rag.initialize()

    logger.info("Initializing database...")
    await init_db()
    await seed_data()

    docs_path = Path(settings.docs_path)
    if not docs_path.exists():
        logger.error(f"Docs path not found: {docs_path}")
        return

    logger.info(f"Processing documents from {docs_path}...")
    count = await rag.add_documents_from_folder(str(docs_path))

    stats = await rag.get_stats()
    logger.info(f"Seeding complete! Added {count} documents. Total in store: {stats['total_documents']}")


if __name__ == "__main__":
    asyncio.run(seed_knowledge_base())

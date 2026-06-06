"""
MedDesk AI - Configuration Manager
Centralized configuration for the entire application (Ollama - Free)
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Ollama (FREE - No API Key)
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama server URL")
    ollama_model: str = Field(default="llama3.1:8b", description="Ollama model name")
    embedding_model: str = Field(default="all-MiniLM-L6-v2", description="Local embedding model")

    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///./meddesk.db")

    # Chainlit
    chainlit_auth_secret: str = Field(default="meddeskai-secret-key-2024")

    # Clinic Info (Indian Context)
    clinic_name: str = Field(default="MedDesk AI")
    clinic_phone: str = Field(default="+91 98765 43210")
    clinic_email: str = Field(default="support@meddeskai.com")
    clinic_address: str = Field(default="201, Sunshine Plaza, MG Road, Andheri West, Mumbai - 400053")
    clinic_hours: str = Field(default="Mon-Sat 9:00 AM - 9:00 PM, Sun: 10:00 AM - 2:00 PM")

    # RAG Configuration
    chunk_size: int = Field(default=1000, description="Document chunk size")
    chunk_overlap: int = Field(default=200, description="Chunk overlap")
    top_k_results: int = Field(default=5, description="Number of retrieved results")
    rerank_top_k: int = Field(default=3, description="After reranking")

    # Escalation
    escalation_threshold: float = Field(default=0.7, description="Sentiment threshold for escalation")
    max_conversation_length: int = Field(default=50, description="Max messages before summary")

    # Paths
    docs_path: Path = Field(default=Path("./docs"))
    vector_store_path: Path = Field(default=Path("./vector_store"))
    data_path: Path = Field(default=Path("./data"))

    # Advanced RAG
    use_hyde: bool = Field(default=False, description="Use HyDE (disabled for Ollama - slower)")
    use_multi_query: bool = Field(default=False, description="Use multi-query (disabled for speed)")
    use_reranking: bool = Field(default=True, description="Use cross-encoder reranking")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def get_settings() -> Settings:
    """Get settings singleton"""
    return Settings()

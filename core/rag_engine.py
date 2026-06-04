"""
CareFirst Medical Center - Advanced RAG Pipeline
Features: Query Rewriting, Hybrid Search, Reranking (Ollama + HuggingFace)
"""
from langchain_ollama import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.documents import Document
from typing import List, Optional, Dict, Any
import hashlib
from datetime import datetime
from pathlib import Path
from loguru import logger


class CareFirstRAG:
    """
    Advanced RAG Pipeline for Medical Receptionist (Ollama + Local Embeddings)
    - Query Rewriting
    - Hybrid Search (MMR)
    - Cross-Encoder Reranking
    """

    def __init__(self, config):
        self.config = config
        self.embeddings = HuggingFaceEmbeddings(
            model_name=config.embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
        self.llm = ChatOllama(
            model=config.ollama_model,
            base_url=config.ollama_base_url,
            temperature=0.3,
            num_ctx=4096
        )
        self.vector_store = None
        self.retriever = None
        self._initialized = False

    async def initialize(self):
        """Initialize the RAG pipeline"""
        if self._initialized:
            return

        # Initialize vector store
        self.vector_store = Chroma(
            collection_name="carefirst_knowledge",
            embedding_function=self.embeddings,
            persist_directory=str(self.config.vector_store_path)
        )

        # Setup base retriever
        base_retriever = self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": self.config.top_k_results,
                "fetch_k": self.config.top_k_results * 2,
                "lambda_mult": 0.7
            }
        )

        # Add reranking if enabled
        self._reranker = None
        if self.config.use_reranking:
            try:
                self._reranker = HuggingFaceCrossEncoder(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
                logger.info("Reranking enabled")
            except Exception as e:
                logger.warning(f"Reranking not available: {e}")

        self.retriever = base_retriever

        self._initialized = True
        logger.info("CareFirst RAG Pipeline initialized successfully")

    async def _rewrite_query(self, query: str, chat_history: List) -> str:
        """Rewrite query based on chat history for better retrieval"""
        if not chat_history:
            return query

        history_context = "\n".join([
            f"{'Human' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
            for m in chat_history[-4:]
        ])

        rewrite_prompt = ChatPromptTemplate.from_template(
            """Given the conversation history and the latest user question, 
            rewrite the question to be a standalone query for document retrieval.
            
            Conversation History:
            {history}
            
            Latest Question: {question}
            
            Standalone Query:"""
        )

        chain = rewrite_prompt | self.llm | StrOutputParser()
        rewritten = await chain.ainvoke({"history": history_context, "question": query})
        return rewritten.strip()

    async def retrieve(self, query: str, chat_history: List = None) -> List[Document]:
        """Retrieve relevant documents with advanced techniques"""
        await self.initialize()

        # Step 1: Query Rewriting
        if chat_history:
            rewritten_query = await self._rewrite_query(query, chat_history)
            logger.info(f"Query rewritten: '{query}' -> '{rewritten_query}'")
        else:
            rewritten_query = query

        # Step 2: Retrieval
        docs = await self.retriever.ainvoke(rewritten_query)

        # Step 3: Rerank if available
        if self._reranker and len(docs) > 1:
            try:
                doc_texts = [doc.page_content for doc in docs]
                scores = self._reranker.score([(rewritten_query, text) for text in doc_texts])
                scored_docs = list(zip(docs, scores))
                scored_docs.sort(key=lambda x: x[1], reverse=True)
                docs = [doc for doc, score in scored_docs[:self.config.rerank_top_k]]
            except Exception as e:
                logger.warning(f"Reranking failed: {e}")

        return docs

    async def query(self, query: str, chat_history: List = None) -> Dict[str, Any]:
        """Full RAG query with retrieval and generation"""
        # Retrieve documents
        docs = await self.retrieve(query, chat_history)

        # Format context
        context = "\n\n---\n\n".join([doc.page_content for doc in docs])
        sources = [
            {
                "content": doc.page_content[:200] + "...",
                "source": doc.metadata.get("source", "Unknown"),
                "page": doc.metadata.get("page", "N/A")
            }
            for doc in docs
        ]

        # Generate response
        response = await self._generate_response(query, context, chat_history)

        return {
            "answer": response,
            "sources": sources,
            "num_docs_retrieved": len(docs),
            "context_used": len(context)
        }

    async def _generate_response(self, query: str, context: str, chat_history: List = None) -> str:
        """Generate response using Ollama LLM with retrieved context"""
        system_prompt = """You are MedDesk AI, a professional and empathetic AI receptionist 
        at CareFirst Medical Center, a clinic in Mumbai, India. You help patients with:
        - Finding doctors and specialists
        - Scheduling appointments
        - Understanding clinic policies, hours, and services
        - Insurance and billing questions (Indian insurance providers)
        - General health information (non-diagnostic)
        - Directions and contact information

        IMPORTANT RULES:
        1. Always be professional, warm, and empathetic
        2. Never provide medical diagnoses or treatment advice
        3. Always cite your sources when providing information
        4. If you don't know something, offer to connect them with staff
        5. For emergencies, always direct to call 108 (ambulance) or 102
        6. When scheduling, collect: patient name, preferred doctor, date/time, reason
        7. Detect frustration and offer escalation to human staff
        8. Prices are in Indian Rupees (₹)
        9. Insurance providers are Indian (Star Health, ICICI Lombard, etc.)
        10. Payment methods include UPI, cards, cash, net banking

        Clinic Information:
        {context}
        """

        messages = [("system", system_prompt.format(context=context))]

        # Add chat history
        if chat_history:
            for msg in chat_history[-6:]:
                if isinstance(msg, HumanMessage):
                    messages.append(("human", msg.content))
                elif isinstance(msg, AIMessage):
                    messages.append(("assistant", msg.content))

        messages.append(("human", query))

        prompt = ChatPromptTemplate.from_messages(messages)
        chain = prompt | self.llm | StrOutputParser()
        return await chain.ainvoke({})

    async def add_document(self, file_path: str, content: Optional[str] = None):
        """Add a document to the knowledge base"""
        await self.initialize()

        if content:
            text = content
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()

        # Split document
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            keep_separator=True
        )
        chunks = splitter.create_documents(
            texts=[text],
            metadatas=[{
                "source": file_path,
                "added_at": datetime.utcnow().isoformat(),
                "doc_type": Path(file_path).suffix
            }]
        )

        # Add to vector store
        self.vector_store.add_documents(chunks)
        logger.info(f"Added {len(chunks)} chunks from {file_path}")
        return len(chunks)

    async def add_documents_from_folder(self, folder_path: str):
        """Bulk add documents from a folder"""
        supported_formats = {".txt", ".md", ".pdf", ".docx"}
        folder = Path(folder_path)
        count = 0

        for file in folder.rglob("*"):
            if file.suffix.lower() in supported_formats:
                try:
                    if file.suffix == ".pdf":
                        from pypdf import PdfReader
                        reader = PdfReader(str(file))
                        text = "\n".join([page.extract_text() for page in reader.pages])
                    elif file.suffix == ".docx":
                        from docx import Document
                        doc = Document(str(file))
                        text = "\n".join([p.text for p in doc.paragraphs])
                    else:
                        text = file.read_text(encoding="utf-8")

                    await self.add_document(str(file), text)
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to process {file}: {e}")

        logger.info(f"Processed {count} documents from {folder_path}")
        return count

    async def search_similar(self, query: str, k: int = 5) -> List[Dict]:
        """Search for similar documents with scores"""
        await self.initialize()
        results = self.vector_store.similarity_search_with_relevance_scores(query, k=k)
        return [
            {
                "content": doc.page_content,
                "source": doc.metadata.get("source", "Unknown"),
                "score": score
            }
            for doc, score in results
        ]

    async def get_stats(self) -> Dict:
        """Get vector store statistics"""
        await self.initialize()
        collection = self.vector_store._collection
        return {
            "total_documents": collection.count(),
            "collection_name": "carefirst_knowledge"
        }

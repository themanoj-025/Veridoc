# Veridoc — Engineering Decisions Log

## Architecture Decisions

### Why FastAPI over Django or Flask?
- FastAPI provides native async support, Pydantic v2 integration, auto-generated OpenAPI docs, and SSE streaming support — all critical for a streaming RAG application.

### Why ChromaDB over Pinecone/Weaviate?
- ChromaDB runs entirely locally, requires zero cloud accounts, persists to disk, and is trivial to containerize. This aligns with the "zero external accounts" requirement.

### Why Ollama over OpenAI/Claude by default?
- Ollama serves open-weight models locally with zero API keys or cloud accounts. The provider abstraction allows swapping in Claude/GPT via a single env var change.

### Why Postgres over SQLite?
- Postgres offers better concurrency, JSON support, array columns (for document_ids), and is production-ready. It runs in Docker Compose with zero configuration.

### Why sentence-transformers for embeddings?
- `all-MiniLM-L6-v2` is small (80MB), CPU-friendly, downloads on first run with no API key, and produces 384-dim embeddings that are competitive with paid alternatives.

### Why hand-rolled pipeline instead of LangChain?
- LangChain adds significant abstraction overhead and hides implementation details. A hand-rolled pipeline is inspectable, interview-defensible, and avoids dependency hell.

### Why BM25 + Dense + RRF + Cross-encoder reranking?
- BM25 handles exact keyword matches that dense retrieval might miss. Dense retrieval captures semantic similarity. RRF merges both fairly. Cross-encoder reranking on top-20 candidates significantly improves precision.

### File encryption approach
- Using Fernet (symmetric AES-128-CBC with HMAC) for at-rest file encryption. Keys derived from a master secret via SHA-256.

### JWT approach
- Short-lived access tokens (30 min) + long-lived refresh tokens (7 days). No session storage needed. Row-level ownership checks on every endpoint using user_id from the JWT sub claim.

## Deferred Decisions (see NEXT_STEPS.md)
- Cloud deployment strategy (Render vs Fly vs AWS)
- OAuth app registration (Google/GitHub)
- Custom domain setup
- Production secrets management

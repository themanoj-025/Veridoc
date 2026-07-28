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

### torch vs ONNX Runtime evaluation (H31)
- **Finding**: `sentence-transformers` (used for both embedding via `SentenceTransformer` and reranking via `CrossEncoder`) depends on `torch` as a core runtime dependency. ONNX Runtime cannot be dropped in as a replacement without replacing or significantly rearchitecting the entire embedding/reranking pipeline.
- **`torchvision`**: Not a dependency of this project — not listed in `requirements.txt` and not imported anywhere in the codebase.
- **`python-pptx`**: Not a dependency of this project — never added to `requirements.txt`, never imported.
- **Recommendation**: Keep `torch` in the stack. The CPU-only `--extra-index-url https://download.pytorch.org/whl/cpu` ensures the smallest possible torch download (no CUDA/cuDNN). If container image size becomes a priority, evaluate `onnxruntime` + `optimum` as a parallel inference path for `sentence-transformers` models — but this is a non-trivial refactor that should only be done if the ~2GB torch image is a proven bottleneck.

### Why hand-rolled pipeline instead of LangChain?
- LangChain adds significant abstraction overhead and hides implementation details. A hand-rolled pipeline is inspectable, interview-defensible, and avoids dependency hell.

### Why BM25 + Dense + RRF + Cross-encoder reranking?
- BM25 handles exact keyword matches that dense retrieval might miss. Dense retrieval captures semantic similarity. RRF merges both fairly. Cross-encoder reranking on top-20 candidates significantly improves precision.

### File encryption approach
- Using Fernet (symmetric AES-128-CBC with HMAC) for at-rest file encryption. Keys derived from a master secret via SHA-256.

### JWT approach
- Short-lived access tokens (30 min) + long-lived refresh tokens (7 days). No session storage needed. Row-level ownership checks on every endpoint using user_id from the JWT sub claim.

### Refresh-token rotation (D17)
- Implemented token rotation: each `/refresh` call consumes the presented refresh token and issues a new one. A consumed token cannot be reused — detected via a blacklist (Redis when available, in-memory fallback).
- **Tradeoff**: No access-token blacklist. Access tokens expire in 30 minutes, so a stolen access token is only valid for 30 minutes. A full blacklist would require Redis/DB lookups on every authenticated request, adding latency. The 30-minute expiry window is an acceptable risk for this application tier.
- **Logout**: Revokes the refresh token server-side, preventing further token refreshes. The access token continues to work until natural expiry (30 min). For applications requiring instant logout, add an access-token blacklist (Redis-backed) and check it in `get_current_user()`.

## Deferred Decisions (see NEXT_STEPS.md)
- Cloud deployment strategy (Render vs Fly vs AWS)
- OAuth app registration (Google/GitHub)
- Custom domain setup
- Production secrets management

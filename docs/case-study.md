# Veridoc — Case Study

## Problem

Knowledge workers spend an estimated 20% of their time searching for information across documents. When they find it, they often can't verify whether the answer is complete or accurate. Existing solutions either:
1. Require cloud subscriptions and send sensitive documents to third-party APIs
2. Hallucinate answers without grounding them in source material
3. Don't provide visible, clickable citations the user can verify

## Solution: Veridoc

Veridoc is a "chat with your documents" RAG application that:
- Runs **100% locally** with no cloud accounts
- Provides **cited, verifiable answers** from uploaded documents
- Supports **multi-document, multi-turn conversations**
- Uses **hybrid search** (BM25 + dense embeddings + cross-encoder reranking) for retrieval quality

## Technical Architecture

### Stack Choice Rationale

**Backend: FastAPI**
- Native async support for SSE streaming
- Pydantic v2 for schema validation
- Auto-generated OpenAPI docs

**Frontend: Next.js + TypeScript**
- Server-side rendering for performance
- TypeScript for type safety
- Tailwind CSS for rapid UI development

**Vector Store: ChromaDB**
- Runs locally, persists to disk
- Zero cloud accounts needed
- Simple API for embedding storage/retrieval

**LLM: Ollama (local)**
- No API keys or cloud accounts
- Open-weight models (llama3.1:8b)
- Pluggable: swap to Claude/GPT via env var

### Key Technical Decisions

1. **Hybrid Retrieval**: BM25 catches exact keyword matches that dense search might miss. Dense search captures semantic similarity. RRF merges both fairly. Cross-encoder reranks top candidates for precision.

2. **Hand-rolled Pipeline**: No LangChain abstraction. Every step (retrieval, reranking, generation, faithfulness checking) is explicit code, making the system inspectable and explainable.

3. **Instruction Boundary**: Retrieved content is separated from system instructions with clear delimiters, preventing prompt injection through document text.

4. **Faithfulness Checking**: Each answer is verified against source context using an LLM-as-judge approach, providing a quantitative faithfulness score.

## Evaluation Results

See [Evaluation Report](evaluation-report.md) for detailed metrics comparing naive dense-only retrieval vs. the full hybrid+rerank pipeline.

## What I'd Change at Scale

1. **Replace ChromaDB with Qdrant/Pinecone**: Chroma works well locally but doesn't scale horizontally. For production, use a distributed vector DB.

2. **Async Ingestion Queue**: Replace in-process `asyncio.create_task` with a proper task queue (Celery + Redis) for reliable async processing.

3. **BM25 Index Persistence**: Currently rebuilds BM25 index on each query. For production, persist the index and update incrementally.

4. **Caching Layer**: Add Redis caching for frequent queries and embeddings to reduce latency.

5. **Distributed LLM Serving**: For high-throughput, use vLLM or TGI instead of raw Ollama.

## Conclusion

Veridoc demonstrates that a production-quality RAG system can be built entirely with open-source, locally-run components. The hybrid retrieval pipeline significantly outperforms naive dense-only retrieval, and the citation system provides verifiable answers that users can trust.

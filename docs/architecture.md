# Veridoc — Architecture

## System Overview

Veridoc is a "chat with your documents" RAG (Retrieval-Augmented Generation) application designed to run entirely locally with zero external accounts.

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                    │
│  ┌─────────────────┐  ┌──────────────────────────────┐  │
│  │  DocumentViewer  │  │        ChatWindow            │  │
│  │  (Split-pane)    │  │  (SSE streaming, citations) │  │
│  └────────┬────────┘  └──────────────┬───────────────┘  │
│           │                          │                    │
│           └──────────HTTPS───────────┘                    │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│              API Gateway (FastAPI)                      │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │  Auth Route  │  │  Doc Route   │  │   Chat Route   │ │
│  │  (JWT)       │  │  (Upload/CRUD)│  │  (SSE Stream) │ │
│  └─────────────┘  └──────┬───────┘  └───────┬────────┘ │
│                          │                   │          │
│  ┌───────────────────────▼───────────────────▼────────┐ │
│  │              Service Layer                         │ │
│  │  ┌──────────┐  ┌──────────┐  ┌────────────────┐   │ │
│  │  │Ingestion│  │Retrieval │  │  LLM Provider  │   │ │
│  │  │Service  │  │Service   │  │  (Ollama/API)  │   │ │
│  │  └────┬─────┘  └────┬─────┘  └───────┬────────┘   │ │
│  └───────┼─────────────┼────────────────┼────────────┘ │
└──────────┼─────────────┼────────────────┼──────────────┘
           │             │                │
┌──────────▼─────────────▼────────────────▼──────────────┐
│                    Infrastructure                       │
│  ┌──────────┐  ┌──────────┐  ┌──────┐  ┌──────────┐   │
│  │ Postgres │  │  Chroma  │  │MinIO │  │  Ollama  │   │
│  │ (Users,  │  │ (Vector  │  │(S3-  │  │ (Local   │   │
│  │  Docs,   │  │  Store)  │  │compat│  │  LLM)    │   │
│  │  Chats)  │  │          │  │Store)│  │          │   │
│  └──────────┘  └──────────┘  └──────┘  └──────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Data Flow

### Ingestion Pipeline
```
Upload → Parse (PyPDF/DOCX/TXT) → OCR (Tesseract) → Chunk (512 tokens, 64 overlap)
→ Embed (all-MiniLM-L6-v2) → Index (ChromaDB) → Save metadata (Postgres)
```

### Query Pipeline
```
Question → Query Rewrite (if follow-up) → Dense Embed → Dense Search (Chroma)
→ BM25 Search (lexical) → RRF Merge → Cross-encoder Rerank (top-5)
→ LLM Generate (with citations) → Faithfulness Check → SSE Stream to UI
```

## Key Design Decisions

1. **Local-first**: All services run in Docker Compose. No cloud accounts needed.
2. **Pluggable LLM**: Ollama by default; switch to Claude/GPT via env var.
3. **Hybrid retrieval**: BM25 + dense embeddings merged via RRF for best recall.
4. **Self-contained**: No external API dependencies for core functionality.
5. **Inspectable**: Hand-rolled pipeline (no LangChain) for transparency.

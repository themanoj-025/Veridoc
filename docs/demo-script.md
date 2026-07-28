# Veridoc — Demo Walkthrough Script

> **Target duration:** 90–120 seconds  
> **Required stack:** `docker compose up` running with frontend (localhost:3000) and backend (localhost:8000)  
> **Recording tool:** OBS Studio, Loom, or any screen-capture software

---

## Scene 1: Landing Page (0–10s)

| Time | Action | Expected UI State |
|------|--------|-------------------|
| 0s | Navigate to `http://localhost:3000` | See the Veridoc login page with app name, tagline, and login/register form |
| 3s | Mouse-over the "Answers you can verify" tagline | Subtle highlight transition on tagline |
| 5s | Click "Register" tab/link | Registration form appears with email, password, full-name fields |

**Narration:**
> "Veridoc lets you upload documents and ask questions in plain English. Every answer comes with clickable citations you can verify. No cloud account needed — it runs entirely on your machine."

---

## Scene 2: Register & Login (10–25s)

| Time | Action | Expected UI State |
|------|--------|-------------------|
| 10s | Type email: `demo@veridoc.app` | Text appears in email field |
| 12s | Type password: `DemoPass123!` | Dots appear in password field |
| 14s | Type name: `Demo User` | Text appears in name field |
| 16s | Click "Create Account" | Loading state on button (spinner or skeleton) |
| 18s | — | Redirect to dashboard — split-pane layout with Document List (left) and empty-state Document Viewer (right) |

**Narration:**
> "After registering, you land on the dashboard. The split-pane layout shows your documents on the left and a reading view on the right. Let's upload a document."

---

## Scene 3: Upload a Document (25–45s)

| Time | Action | Expected UI State |
|------|--------|-------------------|
| 25s | Click "Upload" button | File picker dialog opens |
| 27s | Select a TXT or PDF file from the eval documents (e.g., `data/documents/github_readme.md`) | File dialog closes; upload progress indicator appears |
| 30s | — | Document appears in the list with status "parsing" → "indexing" → "indexed" (skeleton/citation chips animate) |
| 35s | Click the uploaded document in the list | Document title is selected; document viewer pane shows content |
| 40s | Mouse-over the document list | Hover highlighting on the selected document |

**Narration:**
> "Uploading a document triggers the ingestion pipeline: parsing, chunking into paragraphs, embedding into vectors, and indexing in ChromaDB. The status updates live as each stage completes. Let's upload a second document..."

| Time | Action | Expected UI State |
|------|--------|-------------------|
| 42s | Upload a second file (e.g., `data/documents/synthetic_contract.txt`) | Second document appears in list |

---

## Scene 4: Ask a Question (45–70s)

| Time | Action | Expected UI State |
|------|--------|-------------------|
| 45s | Click "Chat" or the chat panel tab | Chat panel opens on the right side |
| 47s | Type in the chat input: *"What is the purpose of this project?"* | Text appears in input box |
| 52s | Press Enter or click Send | — |
| 54s | — | Streaming response appears token by token (see cursor animation) |
| 58s | — | Response finishes with citation chips inline in the answer |
| 62s | **Click a citation chip** | Document viewer pane scrolls to the exact passage and highlights it with a yellow/blue background animation |
| 65s | Mouse-over another citation chip | Tooltip or subtle hover effect appears |

**Narration:**
> "The system retrieves the most relevant passages using hybrid search — BM25 for keyword matching and dense embeddings for semantic similarity, merged via Reciprocal Rank Fusion and re-ranked by a cross-encoder. The answer streams in real time with citation chips you can click."

---

## Scene 5: Ask an Unanswerable Question (70–90s)

| Time | Action | Expected UI State |
|------|--------|-------------------|
| 70s | Type: *"What is the CEO's phone number?"* | Text in input |
| 75s | Press Enter | — |
| 77s | — | Response streams: *"I don't have enough information to answer that. The uploaded documents don't contain any contact information for a CEO."* |
| 82s | — | No citations (no sources matched) |
| 85s | Camera/pointer pans to show the full screen | Clean split-pane layout, document on left, chat on right |

**Narration:**
> "When the answer isn't in the documents, Veridoc says so explicitly. No hallucination, no guessing — just honest refusal. This is enforced by our faithfulness checker, which verifies every answer against the retrieved context before showing it."

---

## Scene 6: Wrap Up (90–100s)

| Time | Action | Expected UI State |
|------|--------|-------------------|
| 90s | Mouse pointer traces the architecture flow | — |
| 95s | Final frame: the Veridoc interface with both documents loaded, answer with citations visible | Full split-pane with highlighted citation |

**Narration:**
> "Veridoc: answers you can verify, not just believe. Built with FastAPI, Next.js, ChromaDB, and Ollama — 100% local, zero cloud accounts required."

---

## Technical Notes

**Prerequisites before recording:**
```bash
# Ensure the stack is running with sample documents loaded
docker compose up -d
python scripts/fetch_eval_data.py
python scripts/build_gold_qa.py
```

**Recommended recording settings:**
- Resolution: 1920×1080 (or 1440×900 minimum)
- Browser: Chrome/Edge in incognito mode (clean state)
- Frame rate: 30 fps
- Mouse cursor: visible, normal size
- Audio: clear voiceover, no background music competing with narration

**Post-processing:**
- Add a thin border around the browser window
- Add lower-third captions for key technical terms (hybrid search, citations, faithfulness check)
- Export as MP4 (H.264), target file size < 10MB for GitHub README embedding

**Ready-to-use commands for the human:**
```bash
# Step 1: Start the stack
docker compose up -d

# Step 2: Load evaluation data
python scripts/fetch_eval_data.py
python scripts/build_gold_qa.py

# Step 3: Open the app
open http://localhost:3000

# Step 4: Start screen recording and follow the script above
# Step 5: Save as veridoc-demo.mp4 and link from README.md
```

---

*Script prepared by Veridoc engineering. The demo walkthrough requires a human with screen-recording access to capture the final video artifact.*

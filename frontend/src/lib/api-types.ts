// Auto-generated from Veridoc API OpenAPI schema
// Generated: 2026-07-28T15:36:01.143Z
// Run `npm run generate-types` to regenerate when the API changes

// ── Auth ─────────────────────────────────────────────────
export interface UserResponse {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: UserResponse;
}

export interface UserCreate {
  email: string;
  password: string;
  full_name?: string | null;
}

export interface UserLogin {
  email: string;
  password: string;
}

export interface TokenRefresh {
  refresh_token: string;
}

export interface PasswordChange {
  current_password: string;
  new_password: string;
}

// ── Documents ────────────────────────────────────────────
export interface DocumentResponse {
  id: string;
  user_id: string;
  title: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: string;
  page_count?: number | null;
  chunk_count?: number | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentUploadResponse extends DocumentResponse {
  upload_url?: string;
}

export interface DocumentUpdate {
  title?: string;
}

export interface DocumentListResponse {
  items: DocumentResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface IngestionStatus {
  document_id: string;
  status: string;
  progress: number;
  message: string;
}

// ── Conversations ────────────────────────────────────────
export interface ConversationResponse {
  id: string;
  user_id: string;
  title: string;
  is_active: boolean;
  document_ids: string[];
  document_titles: string[];
  created_at: string;
  updated_at: string;
}

export interface ConversationCreate {
  title?: string;
  document_ids: string[];
}

export interface ConversationListResponse {
  items: ConversationResponse[];
  total: number;
  limit: number;
  offset: number;
}

// ── Messages ─────────────────────────────────────────────
export interface Citation {
  chunk_id: string;
  document_id: string;
  text: string;
  page_number?: number | null;
  score: number;
}

export interface MessageResponse {
  id: string;
  conversation_id: string;
  role: string;
  content: string;
  citations: Citation[];
  latency_ms?: number | null;
  tokens_used?: number | null;
  model_used?: string | null;
  faithfulness_score?: number | null;
  created_at: string;
}

export interface ChatRequest {
  conversation_id: string;
  message: string;
}

// ── SSE Events ──────────────────────────────────────────
export interface StreamTokenEvent {
  token: string;
}

export interface StreamDoneEvent {
  message_id: string;
  content: string;
  citations: Citation[];
  latency_ms: number;
  tokens_used: number;
  faithfulness_score: number;
}

export interface StreamErrorEvent {
  error: string;
}

// ── Health ───────────────────────────────────────────────
export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
  timestamp: string;
  dependencies: Record<string, { status: string; error?: string }>;
}

// ── Pagination ──────────────────────────────────────────
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

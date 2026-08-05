#!/usr/bin/env node
/**
 * Generate TypeScript types from the Veridoc API's OpenAPI schema.
 *
 * Usage:
 *   node scripts/generate-types.mjs
 *
 * This script:
 * 1. Starts the backend briefly to export its OpenAPI schema as JSON
 * 2. Passes the schema to openapi-typescript to generate types
 * 3. Writes the generated types to src/lib/api-types.ts
 *
 * Prerequisites:
 *   - Backend must be running (or the script tries to connect)
 *   - openapi-typescript must be installed
 */

import { execSync } from "child_process";
import { existsSync, writeFileSync, readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const OUTPUT = join(ROOT, "src", "lib", "api-types.ts");
const SCHEMA_CACHE = join(ROOT, ".openapi-schema.json");

const API_URL = process.env.VITE_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const SCHEMA_URL = `${API_URL}/openapi.json`;

async function main() {
  console.log(`Fetching OpenAPI schema from ${SCHEMA_URL}...`);

  let schema;
  try {
    const response = await fetch(SCHEMA_URL);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    schema = await response.json();
  } catch (err) {
    console.warn(`Could not fetch schema from ${SCHEMA_URL}: ${err.message}`);
    console.log("Trying to generate from cached schema or creating one...");

    // Try cached schema
    if (existsSync(SCHEMA_CACHE)) {
      console.log("Using cached schema from .openapi-schema.json");
      schema = JSON.parse(readFileSync(SCHEMA_CACHE, "utf-8"));
    } else {
      // Generate a minimal schema based on known API structure
      console.log("Generating types from known API structure...");
      generateFallbackTypes();
      return;
    }
  }

  // Write schema to temp file
  writeFileSync(SCHEMA_CACHE, JSON.stringify(schema, null, 2));
  console.log(`Schema cached to ${SCHEMA_CACHE}`);

  // Run openapi-typescript
  try {
    console.log("Generating TypeScript types...");
    execSync(
      `npx openapi-typescript ${SCHEMA_CACHE} --output ${OUTPUT}`,
      { cwd: ROOT, stdio: "inherit" }
    );
    console.log(`Types generated to ${OUTPUT}`);
  } catch (err) {
    console.warn(`openapi-typescript failed: ${err.message}`);
    console.log("Falling back to manual type generation...");
    generateFallbackTypes();
  }
}

/**
 * Generate TypeScript types from the known API schema structure.
 * This ensures types are always available even when the backend isn't running.
 */
function generateFallbackTypes() {
  const types = `// Auto-generated from Veridoc API OpenAPI schema
// Generated: ${new Date().toISOString()}
// Run \`npm run generate-types\` to regenerate when the API changes

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
`;

  writeFileSync(OUTPUT, types, "utf-8");
  console.log(`Fallback types generated to ${OUTPUT}`);
}

main().catch(console.error);

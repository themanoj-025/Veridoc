"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { documents, conversations, documentContent, sharing, apiKeys, searchApi, getApiBase, getAuthHeaders } from "@/lib/api";
import type {
  DocumentResponse,
  ConversationResponse,
} from "@/lib/api-types";

// ── Query key factories ──────────────────────────────────────
// Colocated here so hooks and invalidation share the same keys.

export const queryKeys = {
  documents: {
    all: ["documents"] as const,
    detail: (id: string) => ["documents", id] as const,
  },
  conversations: {
    all: ["conversations"] as const,
    detail: (id: string) => ["conversations", id] as const,
  },
  admin: {
    analytics: ["admin", "analytics"] as const,
    cacheStats: ["admin", "cache-stats"] as const,
    feedbackQueue: ["admin", "feedback-queue"] as const,
  },
} as const;

// ── Document hooks ───────────────────────────────────────────

/** Fetch all documents for the authenticated user. */
export function useDocuments() {
  return useQuery({
    queryKey: queryKeys.documents.all,
    queryFn: async () => {
      const res = await documents.list();
      return (res.data.items ?? []) as DocumentResponse[];
    },
  });
}

/** Fetch a single document by ID. */
export function useDocument(id: string | null) {
  return useQuery({
    queryKey: queryKeys.documents.detail(id ?? "__null__"),
    queryFn: async () => {
      if (!id) throw new Error("No document ID provided");
      const res = await documents.get(id);
      return res.data as DocumentResponse;
    },
    enabled: !!id,
  });
}

// ── Conversation hooks ───────────────────────────────────────

/** Fetch all conversations for the authenticated user. */
export function useConversations() {
  return useQuery({
    queryKey: queryKeys.conversations.all,
    queryFn: async () => {
      const res = await conversations.list();
      return (res.data.items ?? []) as ConversationResponse[];
    },
  });
}

/** Fetch a single conversation by ID (includes messages). */
export function useConversation(id: string | null) {
  return useQuery({
    queryKey: queryKeys.conversations.detail(id ?? "__null__"),
    queryFn: async () => {
      if (!id) throw new Error("No conversation ID provided");
      const res = await conversations.get(id);
      return res.data as ConversationResponse;
    },
    enabled: !!id,
  });
}

/** Mutation to create a new conversation. */
export function useCreateConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { title?: string; document_ids?: string[] }) =>
      conversations.create(data).then((res) => res.data as ConversationResponse),
    onSuccess: (newConv) => {
      // Optimistically add to the list cache
      queryClient.setQueryData<ConversationResponse[]>(
        queryKeys.conversations.all,
        (prev) => (prev ? [newConv, ...prev] : [newConv]),
      );
    },
  });
}

/** Mutation to delete a document. */
export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => documents.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all });
    },
  });
}

/** Mutation to delete a conversation. */
export function useDeleteConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => conversations.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.conversations.all });
    },
  });
}

/** Mutation to upload a document. */
export function useUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ file, title }: { file: File; title?: string }) =>
      documents.upload(file, title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all });
    },
  });
}

// ── Document Content hooks (F19) ─────────────────────────

interface DocChunk {
  id: string;
  index: number;
  content: string;
  page_number: number | null;
  ocr_used: boolean;
}

interface DocumentContent {
  id: string;
  title: string;
  filename: string;
  file_type: string;
  status: string;
  page_count: number | null;
  chunk_count: number | null;
  chunks: DocChunk[];
}

/** Fetch document content with all chunks for the viewer. */
export function useDocumentContent(id: string | null) {
  return useQuery({
    queryKey: ["document-content", id],
    queryFn: async () => {
      if (!id) throw new Error("No document ID provided");
      const res = await documentContent.get(id);
      return res.data as DocumentContent;
    },
    enabled: !!id,
    staleTime: 60_000, // Content rarely changes — cache 1 min
  });
}

// ── Sharing hooks (F20) ──────────────────────────────────

interface DocumentShare {
  id: string;
  document_id: string;
  shared_with_email: string;
  permission: string;
  created_at: string;
}

/** Fetch shares for a document. */
export function useDocumentShares(documentId: string | null) {
  return useQuery({
    queryKey: ["document-shares", documentId],
    queryFn: async () => {
      if (!documentId) throw new Error("No document ID");
      const res = await sharing.list(documentId);
      return (res.data ?? []) as DocumentShare[];
    },
    enabled: !!documentId,
  });
}

// ── API Key hooks (F20) ──────────────────────────────────

interface ApiKeyInfo {
  id: string;
  prefix: string;
  name: string;
  is_active: boolean;
  last_used_at: string | null;
  rate_limit_per_minute: number | null;
  created_at: string;
}

/** Fetch all API keys for the current user. */
export function useApiKeys() {
  return useQuery({
    queryKey: ["api-keys"],
    queryFn: async () => {
      const res = await apiKeys.list();
      return (res.data ?? []) as ApiKeyInfo[];
    },
  });
}

// ── Admin Analytics hooks ────────────────────────────────────

interface AnalyticsData {
  total_queries: number;
  total_users: number;
  total_documents: number;
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  queries_today: number;
  queries_this_week: number;
  most_used_model: string | null;
  avg_estimated_cost: number | null;
  top_documents: { document_id: string; citation_count: number }[];
  recent_queries: { query: string; latency_ms: number; model_used: string; created_at: string | null }[];
  daily_query_volume: { date: string; count: number }[];
}

interface CacheStats {
  hits: number;
  misses: number;
  total: number;
  hit_rate: number;
  memory_entries: number;
  redis_available: boolean;
  enabled: boolean;
  ttl_seconds: number;
}

interface FeedbackEntry {
  feedback: string;
  question: string;
  answer: string;
  faithfulness_score: number | null;
  timestamp: string;
}

interface FeedbackQueue {
  total: number;
  thumbs_down: number;
  thumbs_up: number;
  avg_faithfulness: number;
  recent_entries: FeedbackEntry[];
}

// F13: All admin fetches route through the shared api.ts helpers
// (getApiBase + getAuthHeaders) so auth-header/error handling is uniform.

/** Fetch admin analytics. Returns ``null`` on 403 (no admin access). */
export function useAdminAnalytics() {
  return useQuery({
    queryKey: queryKeys.admin.analytics,
    queryFn: async () => {
      const res = await fetch(
        `${getApiBase()}/api/v1/admin/analytics`,
        { headers: getAuthHeaders() },
      );
      if (res.status === 403) return null;
      if (!res.ok) throw new Error(`Analytics fetch failed: ${res.status}`);
      return (await res.json()) as AnalyticsData;
    },
  });
}

/** Fetch cache stats. Returns ``null`` on 403. */
export function useAdminCacheStats() {
  return useQuery({
    queryKey: queryKeys.admin.cacheStats,
    queryFn: async () => {
      const res = await fetch(
        `${getApiBase()}/api/v1/admin/cache-stats`,
        { headers: getAuthHeaders() },
      );
      if (res.status === 403) return null;
      if (!res.ok) throw new Error(`Cache-stats fetch failed: ${res.status}`);
      return (await res.json()) as CacheStats;
    },
  });
}

/** Fetch feedback queue. Returns ``null`` on 403. */
export function useAdminFeedbackQueue() {
  return useQuery({
    queryKey: queryKeys.admin.feedbackQueue,
    queryFn: async () => {
      const res = await fetch(
        `${getApiBase()}/api/v1/admin/feedback-queue`,
        { headers: getAuthHeaders() },
      );
      if (res.status === 403) return null;
      if (!res.ok) throw new Error(`Feedback fetch failed: ${res.status}`);
      return (await res.json()) as FeedbackQueue;
    },
  });
}

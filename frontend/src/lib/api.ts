"use client";

import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

// Interceptor to attach JWT token
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Interceptor to handle 401 and refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const refreshToken = localStorage.getItem("refresh_token");
        if (refreshToken) {
          const { data } = await axios.post(`${API_BASE}/api/v1/auth/refresh`, {
            refresh_token: refreshToken,
          });
          localStorage.setItem("access_token", data.access_token);
          localStorage.setItem("refresh_token", data.refresh_token);
          originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
          return api(originalRequest);
        }
      } catch {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        if (typeof window !== "undefined") {
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(error);
  }
);

// ── Auth ──
// ── Shared utilities for components using the API client (F13) ──

/** Get the API base URL from env or default */
export function getApiBase(): string {
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
}

/** Get the auth token from localStorage */
export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

/** Build auth headers for manual fetch calls */
export function getAuthHeaders(): Record<string, string> {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

// ── Auth ──
export const auth = {
  register: (email: string, password: string, fullName?: string) =>
    api.post("/api/v1/auth/register", { email, password, full_name: fullName }),
  login: (email: string, password: string) =>
    api.post("/api/v1/auth/login", { email, password }),
  refresh: (refreshToken: string) =>
    api.post("/api/v1/auth/refresh", { refresh_token: refreshToken }),
  me: () => api.get("/api/v1/auth/me"),
  changePassword: (currentPassword: string, newPassword: string) =>
    api.post("/api/v1/auth/change-password", { current_password: currentPassword, new_password: newPassword }),
};

// ── Documents ──
export const documents = {
  upload: (file: File, title?: string) => {
    const formData = new FormData();
    formData.append("file", file);
    if (title) formData.append("title", title);
    return api.post("/api/v1/documents/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  list: () => api.get("/api/v1/documents/"),
  get: (id: string) => api.get(`/api/v1/documents/${id}`),
  update: (id: string, data: { title?: string }) =>
    api.patch(`/api/v1/documents/${id}`, data),
  delete: (id: string) => api.delete(`/api/v1/documents/${id}`),
  reindex: (id: string) => api.post(`/api/v1/documents/${id}/reindex`),
};

// ── Conversations ──
export const conversations = {
  create: (data: { title?: string; document_ids?: string[] }) =>
    api.post("/api/v1/chat/conversations", data),
  list: () => api.get("/api/v1/chat/conversations"),
  get: (id: string) => api.get(`/api/v1/chat/conversations/${id}`),
  delete: (id: string) => api.delete(`/api/v1/chat/conversations/${id}`),
  messages: (id: string) => api.get(`/api/v1/chat/conversations/${id}/messages`),
};

// ── Chat (SSE) with automatic reconnection (F11) ──

interface StreamChatOptions {
  conversationId: string;
  message: string;
  onToken: (token: string) => void;
  onDone: (data: any) => void;
  onError: (error: string) => void;
  maxRetries?: number;
}

interface StreamChatController {
  abort: () => void;
}

/**
 * SSE streaming client with automatic reconnect with exponential backoff (F11).
 *
 * When a stream drops unexpectedly (before receiving a "done" event),
 * it automatically reconnects up to ``maxRetries`` times with exponential
 * backoff (1s, 2s, 4s, 8s, capped at 16s).
 */
export function streamChat({
  conversationId,
  message,
  onToken,
  onDone,
  onError,
  maxRetries = 3,
}: StreamChatOptions): StreamChatController {
  const controller = { aborted: false };

  const startStream = async (retryCount: number) => {
    if (controller.aborted) return;

    const token = localStorage.getItem("access_token");

    try {
      const response = await fetch(`${API_BASE}/api/v1/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ conversation_id: conversationId, message }),
      });

      if (!response.ok) {
        if (response.status === 429) {
          onError("Rate limited. Please wait before sending another message.");
        } else {
          onError(`HTTP ${response.status}`);
        }
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        onError("No response stream");
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";
      let streamDone = false;

      while (!controller.aborted) {
        const { done, value } = await reader.read();
        if (done) {
          streamDone = true;
          break;
        }

        if (controller.aborted) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            continue;
          }
          if (line.startsWith("data: ")) {
            const dataStr = line.slice(6).trim();
            try {
              const data = JSON.parse(dataStr);
              if (data.token) {
                onToken(data.token);
              } else if (data.content) {
                streamDone = true;
                onDone(data);
              } else if (data.error) {
                onError(data.error);
                streamDone = true;
              }
            } catch {
              // Incomplete JSON, wait for more data
            }
          }
        }
      }

      // If the stream ended without a "done" event and we still have retries, reconnect
      if (!streamDone && !controller.aborted && retryCount < maxRetries) {
        const delay = Math.min(1000 * Math.pow(2, retryCount), 16000);
        console.log(`SSE stream disconnected, reconnecting in ${delay}ms (attempt ${retryCount + 1}/${maxRetries})...`);
        setTimeout(() => startStream(retryCount + 1), delay);
      }
    } catch (err: any) {
      if (err.name === "AbortError" || controller.aborted) return;

      // Network error — retry with backoff
      if (retryCount < maxRetries) {
        const delay = Math.min(1000 * Math.pow(2, retryCount), 16000);
        console.log(`SSE stream error, reconnecting in ${delay}ms (attempt ${retryCount + 1}/${maxRetries})...`);
        setTimeout(() => startStream(retryCount + 1), delay);
      } else {
        onError("Connection lost after multiple retries. Please try again.");
      }
    }
  };

  startStream(0);

  return {
    abort: () => {
      controller.aborted = true;
    },
  };
}

// ── Document Content (F19) ────────────────────────────
export const documentContent = {
  /** Fetch document content with all chunks for the viewer. */
  get: (documentId: string) =>
    api.get(`/api/v1/documents/${documentId}/content`),
};

// ── Document Sharing (F20) ────────────────────────────
export const sharing = {
  /** List shares for a document. */
  list: (documentId: string) =>
    api.get(`/api/v1/documents/${documentId}/shares`),
  /** Share a document with another user. */
  create: (documentId: string, data: { shared_with_email: string; permission?: string }) =>
    api.post(`/api/v1/documents/${documentId}/shares`, data),
  /** Update share permission. */
  update: (shareId: string, data: { permission: string }) =>
    api.patch(`/api/v1/shares/${shareId}`, data),
  /** Remove a share. */
  delete: (shareId: string) =>
    api.delete(`/api/v1/shares/${shareId}`),
};

// ── API Keys (F20) ────────────────────────────────────
export const apiKeys = {
  /** List all API keys for the current user. */
  list: () => api.get("/api/v1/api-keys"),
  /** Create a new API key (returns the full key once). */
  create: (data: { name: string; rate_limit_per_minute?: number }) =>
    api.post("/api/v1/api-keys", data),
  /** Revoke (delete) an API key. */
  delete: (keyId: string) =>
    api.delete(`/api/v1/api-keys/${keyId}`),
};

// ── Search ──────────────────────────────────────────────
export const searchApi = {
  fulltext: (q: string, documentId?: string, limit: number = 20, offset: number = 0) =>
    api.get("/api/v1/search/fulltext", {
      params: { q, document_id: documentId, limit, offset },
    }),
};

export default api;

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

// ── Chat (SSE) ──
export function streamChat(
  conversationId: string,
  message: string,
  onToken: (token: string) => void,
  onDone: (data: any) => void,
  onError: (error: string) => void
): AbortController {
  const controller = new AbortController();
  const token = localStorage.getItem("access_token");

  fetch(`${API_BASE}/api/v1/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ conversation_id: conversationId, message }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        onError(`HTTP ${response.status}`);
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        onError("No response stream");
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            const event = line.slice(7).trim();
            // Next line should be data
            continue;
          }
          if (line.startsWith("data: ")) {
            const dataStr = line.slice(6).trim();
            try {
              const data = JSON.parse(dataStr);
              if (data.token) {
                onToken(data.token);
              } else if (data.content) {
                onDone(data);
              } else if (data.error) {
                onError(data.error);
              }
            } catch {
              // Incomplete JSON, wait for more data
            }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError(err.message);
      }
    });

  return controller;
}

export default api;

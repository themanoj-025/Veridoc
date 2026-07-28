"use client";

import { create } from "zustand";
import type { UserResponse } from "@/lib/api-types";

type User = UserResponse;

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setUser: (user: User | null) => void;
  login: (accessToken: string, refreshToken: string, user: User) => void;
  logout: () => void;
  checkAuth: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,

  setUser: (user) => set({ user, isAuthenticated: !!user, isLoading: false }),

  login: (accessToken, refreshToken, user) => {
    localStorage.setItem("access_token", accessToken);
    localStorage.setItem("refresh_token", refreshToken);
    set({ user, isAuthenticated: true, isLoading: false });
  },

  logout: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    set({ user: null, isAuthenticated: false, isLoading: false });
  },

  checkAuth: () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      set({ user: null, isAuthenticated: false, isLoading: false });
      return;
    }
    // Try to decode the JWT to get user info
    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      // Fetch user from API
      import("./api").then(({ auth }) => {
        auth.me().then((res) => {
          set({ user: res.data, isAuthenticated: true, isLoading: false });
        }).catch(() => {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          set({ user: null, isAuthenticated: false, isLoading: false });
        });
      });
    } catch {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },
}));

interface ChatState {
  streamingContent: string;
  isStreaming: boolean;
  setStreamingContent: (content: string) => void;
  appendToken: (token: string) => void;
  setStreaming: (isStreaming: boolean) => void;
  resetStreaming: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  streamingContent: "",
  isStreaming: false,

  setStreamingContent: (content) => set({ streamingContent: content }),
  appendToken: (token) =>
    set((state) => ({ streamingContent: state.streamingContent + token })),
  setStreaming: (isStreaming) => set({ isStreaming }),
  resetStreaming: () => set({ streamingContent: "", isStreaming: false }),
}));

interface DocumentState {
  selectedDocumentId: string | null;
  setSelectedDocument: (id: string | null) => void;
}

export const useDocumentStore = create<DocumentState>((set) => ({
  selectedDocumentId: null,
  setSelectedDocument: (id) => set({ selectedDocumentId: id }),
}));

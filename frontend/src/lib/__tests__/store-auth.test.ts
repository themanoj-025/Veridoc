import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { useAuthStore } from "@/lib/store";

// ── Mock localStorage ───────────────────────────────────
// (setup.ts provides a mock, but we add cleanup here)

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  useAuthStore.setState({
    user: null,
    isAuthenticated: false,
    isLoading: true,
  });
});

afterEach(() => {
  localStorage.clear();
});

// ── AuthStore ───────────────────────────────────────────

describe("AuthStore — initial state", () => {
  it("starts with null user", () => {
    useAuthStore.setState({ isLoading: false });
    expect(useAuthStore.getState().user).toBeNull();
  });

  it("starts as not authenticated", () => {
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });

  it("starts with loading true", () => {
    expect(useAuthStore.getState().isLoading).toBe(true);
  });
});

describe("AuthStore — setUser", () => {
  it("sets user and marks authenticated", () => {
    const user = { id: "u1", email: "a@b.com", full_name: "Alice", is_active: true, is_verified: true, created_at: "2024-01-01" };
    useAuthStore.getState().setUser(user);
    expect(useAuthStore.getState().user).toEqual(user);
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(useAuthStore.getState().isLoading).toBe(false);
  });

  it("clears user when set to null", () => {
    useAuthStore.getState().setUser(null);
    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAuthStore.getState().isLoading).toBe(false);
  });
});

describe("AuthStore — login", () => {
  it("stores tokens in localStorage", () => {
    const user = { id: "u1", email: "a@b.com", full_name: "Alice", is_active: true, is_verified: true, created_at: "2024-01-01" };
    useAuthStore.getState().login("access-123", "refresh-456", user);
    expect(localStorage.getItem("access_token")).toBe("access-123");
    expect(localStorage.getItem("refresh_token")).toBe("refresh-456");
  });

  it("sets user and auth state", () => {
    const user = { id: "u1", email: "a@b.com", full_name: "Alice", is_active: true, is_verified: true, created_at: "2024-01-01" };
    useAuthStore.getState().login("access-123", "refresh-456", user);
    expect(useAuthStore.getState().user).toEqual(user);
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(useAuthStore.getState().isLoading).toBe(false);
  });

  it("overwrites previous auth state", () => {
    const user1 = { id: "u1", email: "first@test.com", full_name: "First", is_active: true, is_verified: true, created_at: "2024-01-01" };
    const user2 = { id: "u2", email: "second@test.com", full_name: "Second", is_active: true, is_verified: true, created_at: "2024-01-01" };
    useAuthStore.getState().login("old-access", "old-refresh", user1);
    useAuthStore.getState().login("new-access", "new-refresh", user2);
    expect(useAuthStore.getState().user?.id).toBe("u2");
    expect(localStorage.getItem("access_token")).toBe("new-access");
  });
});

describe("AuthStore — logout", () => {
  it("removes tokens from localStorage", () => {
    localStorage.setItem("access_token", "some-token");
    localStorage.setItem("refresh_token", "some-refresh");
    useAuthStore.getState().logout();
    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
  });

  it("clears user and auth state", () => {
    const user = { id: "u1", email: "a@b.com", full_name: "Alice", is_active: true, is_verified: true, created_at: "2024-01-01" };
    useAuthStore.getState().login("access", "refresh", user);
    useAuthStore.getState().logout();
    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });

  it("sets isLoading to false", () => {
    useAuthStore.getState().logout();
    expect(useAuthStore.getState().isLoading).toBe(false);
  });
});

describe("AuthStore — checkAuth (no token)", () => {
  it("sets unauthenticated when no token exists", () => {
    useAuthStore.getState().checkAuth();
    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAuthStore.getState().isLoading).toBe(false);
  });
});

describe("AuthStore — checkAuth (with invalid token)", () => {
  it("fails gracefully with malformed token", () => {
    localStorage.setItem("access_token", "not-a-valid-jwt");
    useAuthStore.getState().checkAuth();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAuthStore.getState().user).toBeNull();
  });
});

describe("AuthStore — loading lifecycle transitions", () => {
  it("transitions: loading -> authenticated -> unauthenticated", () => {
    // Start: loading
    expect(useAuthStore.getState().isLoading).toBe(true);
    expect(useAuthStore.getState().isAuthenticated).toBe(false);

    // Login: authenticated
    const user = { id: "u1", email: "a@b.com", full_name: "A", is_active: true, is_verified: true, created_at: "2024-01-01" };
    useAuthStore.getState().login("at", "rt", user);
    expect(useAuthStore.getState().isLoading).toBe(false);
    expect(useAuthStore.getState().isAuthenticated).toBe(true);

    // Logout: unauthenticated
    useAuthStore.getState().logout();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAuthStore.getState().user).toBeNull();
  });

  it("transitions: loading -> unauthenticated (no token)", () => {
    useAuthStore.getState().checkAuth();
    expect(useAuthStore.getState().isLoading).toBe(false);
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });
});

describe("AuthStore — edge cases", () => {
  it("handles double login without errors", () => {
    const user = { id: "u1", email: "a@b.com", full_name: "A", is_active: true, is_verified: true, created_at: "2024-01-01" };
    useAuthStore.getState().login("t1", "r1", user);
    useAuthStore.getState().login("t2", "r2", user);
    expect(localStorage.getItem("access_token")).toBe("t2");
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
  });

  it("handles double logout without errors", () => {
    useAuthStore.getState().logout();
    useAuthStore.getState().logout();
    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });

  it("handles login after logout", () => {
    const user = { id: "u1", email: "a@b.com", full_name: "A", is_active: true, is_verified: true, created_at: "2024-01-01" };
    useAuthStore.getState().login("t1", "r1", user);
    useAuthStore.getState().logout();
    useAuthStore.getState().login("t2", "r2", user);
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(localStorage.getItem("access_token")).toBe("t2");
  });
});

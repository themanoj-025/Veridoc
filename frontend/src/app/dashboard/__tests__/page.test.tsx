import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { useAuthStore, useChatStore, useDocumentStore } from "@/lib/store";

// ── Mocks ───────────────────────────────────────────────

const mockPush = vi.fn();
const mockReplace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
    prefetch: vi.fn(),
  }),
}));

vi.mock("@/lib/api", () => ({
  documents: {
    list: vi.fn().mockResolvedValue({ data: { items: [], total: 0 } }),
    upload: vi.fn().mockResolvedValue({ data: { id: "doc-1" } }),
  },
  conversations: {
    list: vi.fn().mockResolvedValue({ data: { items: [], total: 0 } }),
    create: vi.fn().mockResolvedValue({ data: { id: "conv-1", title: "New Chat", document_ids: [] } }),
    messages: vi.fn().mockResolvedValue({ data: [] }),
  },
  auth: {
    me: vi.fn().mockResolvedValue({ data: { id: "user-1", email: "test@test.com", full_name: "Test User" } }),
  },
  searchApi: {
    fulltext: vi.fn().mockResolvedValue({ data: { results: [], total: 0 } }),
  },
  streamChat: vi.fn(),
}));

// ── Helpers ─────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.setState({
    user: null,
    isAuthenticated: false,
    isLoading: true,
  });
  useChatStore.getState().resetStreaming();
  useDocumentStore.getState().setSelectedDocument(null);
  localStorage.clear();
});

async function renderDashboard() {
  const Dashboard = (await import("@/app/dashboard/page")).default;
  return render(<Dashboard />);
}

const sampleUser = {
  id: "user-1",
  email: "test@test.com",
  full_name: "Test User",
  is_active: true,
  is_verified: true,
  created_at: "2024-01-01",
};

// ── Tests ───────────────────────────────────────────────

describe("Dashboard page — loading state", () => {
  it("shows loading indicator when isLoading is true", async () => {
    useAuthStore.setState({ isLoading: true, isAuthenticated: false });
    const { container } = await renderDashboard();
    expect(container.textContent).toContain("Loading Veridoc");
  });

  it("shows animated loading box", async () => {
    useAuthStore.setState({ isLoading: true });
    const { container } = await renderDashboard();
    const loader = container.querySelector(".animate-pulse-slow");
    expect(loader).not.toBeNull();
  });
});

describe("Dashboard page — auth redirect", () => {
  it("redirects to /login when not authenticated and not loading", async () => {
    useAuthStore.setState({ isLoading: false, isAuthenticated: false });
    await renderDashboard();
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/login");
    });
  });

  it("does not redirect when authenticated", async () => {
    useAuthStore.setState({ isLoading: false, isAuthenticated: true, user: sampleUser });
    await renderDashboard();
    await waitFor(() => {
      expect(mockReplace).not.toHaveBeenCalled();
    });
  });

  it("does not redirect while still loading", async () => {
    useAuthStore.setState({ isLoading: true, isAuthenticated: false });
    await renderDashboard();
    expect(mockReplace).not.toHaveBeenCalled();
  });
});

describe("Dashboard page — authenticated state", () => {
  beforeEach(() => {
    useAuthStore.setState({ isLoading: false, isAuthenticated: true, user: sampleUser });
  });

  it("renders the Veridoc header", async () => {
    await renderDashboard();
    expect(screen.getByText("Veridoc")).toBeDefined();
  });

  it("renders the sign out button", async () => {
    await renderDashboard();
    expect(screen.getByText("Sign out")).toBeDefined();
  });

  it("renders the theme toggle after mount", async () => {
    await renderDashboard();
    // ThemeToggle renders a placeholder div until useEffect fires;
    // wait for the actual toggle button with aria-label to appear
    await waitFor(() => {
      const toggle = screen.getByLabelText(/switch to (light|dark) mode/i);
      expect(toggle).toBeDefined();
    });
  });

  it("shows user email in header", async () => {
    await renderDashboard();
    expect(screen.getByText("test@test.com")).toBeDefined();
  });

  it("renders GDPR export button", async () => {
    await renderDashboard();
    const exportBtn = screen.getByLabelText("Export data");
    expect(exportBtn).toBeDefined();
  });

  it("renders GDPR delete button", async () => {
    await renderDashboard();
    const deleteBtn = screen.getByLabelText("Delete account");
    expect(deleteBtn).toBeDefined();
  });

  it("renders mobile bottom nav buttons", async () => {
    await renderDashboard();
    const docsButtons = screen.getAllByText("Docs");
    expect(docsButtons.length).toBeGreaterThanOrEqual(1);
    const chatButtons = screen.getAllByText("Chat");
    expect(chatButtons.length).toBeGreaterThanOrEqual(1);
  });
});

describe("Dashboard page — delete account dialog", () => {
  beforeEach(() => {
    useAuthStore.setState({ isLoading: false, isAuthenticated: true, user: sampleUser });
  });

  it("shows delete confirmation when delete button is clicked", async () => {
    await renderDashboard();
    const deleteBtn = screen.getByLabelText("Delete account");
    fireEvent.click(deleteBtn);
    await waitFor(() => {
      expect(screen.getByText("Delete Account")).toBeDefined();
    });
    expect(screen.getByText(/This action cannot be undone/)).toBeDefined();
  });

  it("has Cancel and confirm buttons in delete confirmation", async () => {
    await renderDashboard();
    const deleteBtn = screen.getByLabelText("Delete account");
    fireEvent.click(deleteBtn);
    await waitFor(() => {
      expect(screen.getByText("Cancel")).toBeDefined();
      expect(screen.getByText("Yes, delete my account")).toBeDefined();
    });
  });
});

describe("Dashboard page — mobile view switching", () => {
  beforeEach(() => {
    useAuthStore.setState({ isLoading: false, isAuthenticated: true, user: sampleUser });
  });

  it("switches to chat view on chat tab click", async () => {
    await renderDashboard();
    const chatButtons = screen.getAllByText("Chat");
    fireEvent.click(chatButtons[0]);
    await waitFor(() => {
      // ChatPanel renders "+ New Chat" button in header
      expect(screen.getByText("+ New Chat")).toBeDefined();
    });
  });

  it("switches to docs view on docs tab click", async () => {
    await renderDashboard();
    const docsButtons = screen.getAllByText("Docs");
    fireEvent.click(docsButtons[0]);
    expect(screen.getByText("Veridoc")).toBeDefined();
  });
});

describe("Dashboard page — logout", () => {
  beforeEach(() => {
    useAuthStore.setState({ isLoading: false, isAuthenticated: true, user: sampleUser });
  });

  it("logs out and redirects to login", async () => {
    await renderDashboard();
    const signOutBtn = screen.getByText("Sign out");
    fireEvent.click(signOutBtn);
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(mockReplace).toHaveBeenCalledWith("/login");
  });
});

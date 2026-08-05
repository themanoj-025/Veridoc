import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ThumbsUpDown } from "@/components/ThumbsUpDown";
import { useToastStore } from "@/lib/toast-store";

const defaultProps = {
  messageId: "msg-1",
  conversationId: "conv-1",
  question: "What is the capital of France?",
  answer: "Paris",
  citations: [{ chunk_id: "c1", document_id: "d1", text: "Paris is the capital", score: 0.95 }],
  faithfulnessScore: 0.92,
};

beforeEach(() => {
  useToastStore.getState().clearToasts();
  // Mock fetch to return success
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({}),
  } as Response);
});

describe("ThumbsUpDown", () => {
  it("renders thumbs up and down buttons", () => {
    render(<ThumbsUpDown {...defaultProps} />);
    expect(screen.getByLabelText("Thumbs up")).toBeInTheDocument();
    expect(screen.getByLabelText("Thumbs down")).toBeInTheDocument();
  });

  it("shows 'Was this helpful?' text", () => {
    render(<ThumbsUpDown {...defaultProps} />);
    expect(screen.getByText("Was this helpful?")).toBeInTheDocument();
  });

  it("sends feedback on thumbs up click", async () => {
    render(<ThumbsUpDown {...defaultProps} />);
    fireEvent.click(screen.getByLabelText("Thumbs up"));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/chat/feedback"),
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining('"feedback":"up"'),
        })
      );
    });
  });

  it("sends feedback on thumbs down click", async () => {
    render(<ThumbsUpDown {...defaultProps} />);
    fireEvent.click(screen.getByLabelText("Thumbs down"));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/chat/feedback"),
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining('"feedback":"down"'),
        })
      );
    });
  });

  it("disables buttons after submitting", async () => {
    render(<ThumbsUpDown {...defaultProps} />);
    fireEvent.click(screen.getByLabelText("Thumbs up"));

    await waitFor(() => {
      expect(screen.getByLabelText("Thumbs up")).toBeDisabled();
    });
  });

  it("shows success toast on thumbs up", async () => {
    render(<ThumbsUpDown {...defaultProps} />);
    fireEvent.click(screen.getByLabelText("Thumbs up"));

    await waitFor(() => {
      const toasts = useToastStore.getState().toasts;
      expect(toasts.length).toBeGreaterThan(0);
      expect(toasts[0].title).toBe("Thanks for your feedback!");
    });
  });

  it("shows info toast on thumbs down", async () => {
    render(<ThumbsUpDown {...defaultProps} />);
    fireEvent.click(screen.getByLabelText("Thumbs down"));

    await waitFor(() => {
      const toasts = useToastStore.getState().toasts;
      expect(toasts.length).toBeGreaterThan(0);
      expect(toasts[0].title).toBe("Feedback recorded");
    });
  });
});

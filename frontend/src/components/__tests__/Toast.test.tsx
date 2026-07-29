import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { ToastContainer } from "@/components/Toast";
import { useToastStore } from "@/lib/toast-store";

beforeEach(() => {
  useToastStore.getState().clearToasts();
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("ToastContainer", () => {
  it("renders nothing when there are no toasts", () => {
    const { container } = render(<ToastContainer />);
    expect(container.innerHTML).toBe("");
  });

  it("renders all active toasts", () => {
    act(() => {
      useToastStore.getState().addToast({ type: "success", title: "Done!" });
      useToastStore.getState().addToast({ type: "error", title: "Failed" });
    });
    render(<ToastContainer />);
    expect(screen.getByText("Done!")).toBeInTheDocument();
    expect(screen.getByText("Failed")).toBeInTheDocument();
  });

  it("renders toast with message", () => {
    act(() => {
      useToastStore.getState().addToast({ type: "info", title: "Info", message: "Details" });
    });
    render(<ToastContainer />);
    expect(screen.getByText("Info")).toBeInTheDocument();
    expect(screen.getByText("Details")).toBeInTheDocument();
  });

  it("renders toast with action button", () => {
    const onClick = vi.fn();
    act(() => {
      useToastStore.getState().addToast({
        type: "warning",
        title: "Warning",
        action: { label: "Undo", onClick },
      });
    });
    render(<ToastContainer />);
    const actionBtn = screen.getByText("Undo");
    expect(actionBtn).toBeInTheDocument();
    fireEvent.click(actionBtn);
    expect(onClick).toHaveBeenCalled();
  });

  it("dismisses toast on close button click", () => {
    act(() => {
      useToastStore.getState().addToast({ type: "success", title: "Dismiss me" });
    });
    render(<ToastContainer />);
    expect(screen.getByText("Dismiss me")).toBeInTheDocument();

    const dismissBtn = screen.getByLabelText("Dismiss");
    fireEvent.click(dismissBtn);

    // After 200ms (animation duration), toast should be removed
    act(() => {
      vi.advanceTimersByTime(250);
    });

    expect(screen.queryByText("Dismiss me")).not.toBeInTheDocument();
  });

  it("auto-dismisses after default duration (4000ms)", () => {
    act(() => {
      useToastStore.getState().addToast({ type: "success", title: "Auto dismiss" });
    });
    render(<ToastContainer />);
    expect(screen.getByText("Auto dismiss")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(3999);
    });
    expect(screen.getByText("Auto dismiss")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(10); // 4009ms total
    });
    // After animation delay
    act(() => {
      vi.advanceTimersByTime(250);
    });
    expect(screen.queryByText("Auto dismiss")).not.toBeInTheDocument();
  });
});

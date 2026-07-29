import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ThemeToggle } from "@/components/ThemeToggle";

beforeEach(() => {
  localStorage.clear();
  document.documentElement.classList.remove("dark");
  // Mock matchMedia for default light mode
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  });
});

describe("ThemeToggle", () => {
  it("renders a toggle button", () => {
    render(<ThemeToggle />);
    const button = screen.getByRole("button");
    expect(button).toBeInTheDocument();
    expect(button).toHaveAttribute("aria-label");
  });

  it("renders a toggle button with correct aria-label in light mode", () => {
    // Default light mode - should show moon icon
    render(<ThemeToggle />);
    const button = screen.getByRole("button");
    expect(button).toHaveAttribute("aria-label", "Switch to light mode");
  });

  it("toggles theme on click", () => {
    render(<ThemeToggle />);
    const button = screen.getByRole("button");

    // Click to toggle
    fireEvent.click(button);

    // Should add dark class
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(localStorage.getItem("theme")).toBe("dark");
  });

  it("toggles back to light on second click", () => {
    render(<ThemeToggle />);
    const button = screen.getByRole("button");

    // First click - dark
    fireEvent.click(button);
    expect(document.documentElement.classList.contains("dark")).toBe(true);

    // Second click - light
    fireEvent.click(button);
    expect(document.documentElement.classList.contains("dark")).toBe(false);
    expect(localStorage.getItem("theme")).toBe("light");
  });
});

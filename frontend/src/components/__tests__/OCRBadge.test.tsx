import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { OCRBadge } from "@/components/OCRBadge";

describe("OCRBadge", () => {
  it("renders the badge when ocrUsed is true", () => {
    render(<OCRBadge ocrUsed={true} />);

    const badge = screen.getByText("OCR");
    expect(badge).toBeDefined();

    // Should have accessible label
    const badgeWithLabel = screen.getByLabelText("OCR extracted content");
    expect(badgeWithLabel).toBeDefined();
  });

  it("renders nothing when ocrUsed is false", () => {
    const { container } = render(<OCRBadge ocrUsed={false} />);
    expect(container.firstChild).toBeNull();
  });

  it("uses xs size by default", () => {
    render(<OCRBadge ocrUsed={true} />);
    const badge = screen.getByText("OCR");
    // xs size applies text-[10px] class
    expect(badge.className).toContain("text-[10px]");
  });

  it("can use sm size", () => {
    render(<OCRBadge ocrUsed={true} size="sm" />);
    const badge = screen.getByText("OCR");
    // sm size applies text-xs class
    expect(badge.className).toContain("text-xs");
  });

  it("accepts additional className", () => {
    render(<OCRBadge ocrUsed={true} className="ml-2" />);
    const badge = screen.getByText("OCR");
    expect(badge.className).toContain("ml-2");
  });

  it("has the correct tooltip title", () => {
    render(<OCRBadge ocrUsed={true} />);
    const badge = screen.getByText("OCR");
    expect(badge.getAttribute("title")).toContain("OCR");
  });
});

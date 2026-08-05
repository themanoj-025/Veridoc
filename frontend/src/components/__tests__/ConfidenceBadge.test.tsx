import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";

// G1: Per-answer confidence badge — combines retrieval + faithfulness scores
// into a single High/Medium/Low indicator, distinct from the OCR badge.

describe("ConfidenceBadge (G1)", () => {
  it("renders High confidence when both scores >= 0.8", () => {
    render(<ConfidenceBadge retrievalScore={0.9} faithfulnessScore={0.95} />);
    expect(screen.getByText("High confidence")).toBeDefined();
    expect(screen.getByLabelText("Answer confidence: high")).toBeDefined();
  });

  it("renders Medium confidence when scores are between 0.5 and 0.8", () => {
    render(<ConfidenceBadge retrievalScore={0.6} faithfulnessScore={0.7} />);
    expect(screen.getByText("Medium confidence")).toBeDefined();
    expect(screen.getByLabelText("Answer confidence: medium")).toBeDefined();
  });

  it("renders Medium confidence when one score is high and the other medium", () => {
    render(<ConfidenceBadge retrievalScore={0.95} faithfulnessScore={0.6} />);
    expect(screen.getByText("Medium confidence")).toBeDefined();
  });

  it("renders Low confidence when either score < 0.5", () => {
    render(<ConfidenceBadge retrievalScore={0.2} faithfulnessScore={0.9} />);
    expect(screen.getByText("Low confidence")).toBeDefined();
    expect(screen.getByLabelText("Answer confidence: low")).toBeDefined();
  });

  it("renders Low confidence when scores are missing", () => {
    render(<ConfidenceBadge />);
    expect(screen.getByText("Low confidence")).toBeDefined();
  });

  it("renders Low confidence when only one score is present and low", () => {
    render(<ConfidenceBadge retrievalScore={null} faithfulnessScore={0.9} />);
    expect(screen.getByText("Low confidence")).toBeDefined();
  });

  it("renders badge in sm size when requested", () => {
    render(
      <ConfidenceBadge retrievalScore={0.9} faithfulnessScore={0.9} size="sm" />
    );
    expect(screen.getByText("High confidence")).toBeDefined();
  });
});

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  Skeleton,
  DocumentListSkeleton,
  ChatMessageSkeleton,
  ConversationListSkeleton,
  DocumentViewerSkeleton,
  UploadProgressSkeleton,
  IngestionSkeleton,
} from "@/components/Skeleton";

describe("Skeleton", () => {
  it("renders with default classes", () => {
    const { container } = render(<Skeleton />);
    const el = container.firstChild as HTMLElement;
    expect(el).toBeInTheDocument();
    expect(el.className).toContain("animate-pulse");
    expect(el.className).toContain("rounded");
  });

  it("renders with custom className", () => {
    const { container } = render(<Skeleton className="w-10 h-10" />);
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain("w-10");
    expect(el.className).toContain("h-10");
  });

  it("is hidden from accessibility tree", () => {
    render(<Skeleton />);
    const el = document.querySelector('[aria-hidden="true"]');
    expect(el).toBeInTheDocument();
  });
});

describe("DocumentListSkeleton", () => {
  it("renders 4 skeleton items", () => {
    const { container } = render(<DocumentListSkeleton />);
    const skeletons = container.querySelectorAll('[aria-hidden="true"]');
    expect(skeletons.length).toBeGreaterThanOrEqual(4);
  });
});

describe("ChatMessageSkeleton", () => {
  it("renders both user and assistant placeholders", () => {
    const { container } = render(<ChatMessageSkeleton />);
    const skeletons = container.querySelectorAll('[aria-hidden="true"]');
    expect(skeletons.length).toBeGreaterThanOrEqual(5);
  });
});

describe("ConversationListSkeleton", () => {
  it("renders 3 placeholder rows", () => {
    const { container } = render(<ConversationListSkeleton />);
    const skeletons = container.querySelectorAll('[aria-hidden="true"]');
    expect(skeletons.length).toBe(3);
  });
});

describe("DocumentViewerSkeleton", () => {
  it("renders multiple skeleton elements", () => {
    const { container } = render(<DocumentViewerSkeleton />);
    const skeletons = container.querySelectorAll('[aria-hidden="true"]');
    expect(skeletons.length).toBeGreaterThanOrEqual(4);
  });
});

describe("UploadProgressSkeleton", () => {
  it("renders with default progress 0", () => {
    render(<UploadProgressSkeleton />);
    expect(screen.getByText("0%")).toBeInTheDocument();
    expect(screen.getByText("Processing...")).toBeInTheDocument();
  });

  it("renders with custom progress", () => {
    render(<UploadProgressSkeleton progress={75} />);
    expect(screen.getByText("75%")).toBeInTheDocument();
  });
});

describe("IngestionSkeleton", () => {
  it("renders all ingestion stages", () => {
    const { container } = render(<IngestionSkeleton />);
    const skeletons = container.querySelectorAll('[aria-hidden="true"]');
    expect(skeletons.length).toBeGreaterThanOrEqual(1);
  });
});

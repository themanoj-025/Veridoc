import { describe, it, expect } from "vitest";
import { cn, formatFileSize, truncate, getFileIcon } from "@/lib/utils";

describe("cn", () => {
  it("merges class names", () => {
    expect(cn("px-4", "py-2")).toBe("px-4 py-2");
  });

  it("handles conditional classes", () => {
    expect(cn("base", false && "hidden", "visible")).toBe("base visible");
  });

  it("resolves tailwind conflicts", () => {
    // twMerge should keep the last conflicting class
    expect(cn("px-2", "px-4")).toBe("px-4");
  });
});

describe("formatFileSize", () => {
  it("returns '0 B' for zero bytes", () => {
    expect(formatFileSize(0)).toBe("0 B");
  });

  it("formats bytes", () => {
    expect(formatFileSize(500)).toBe("500.0 B");
  });

  it("formats kilobytes", () => {
    expect(formatFileSize(2048)).toBe("2.0 KB");
  });

  it("formats megabytes", () => {
    expect(formatFileSize(5 * 1024 * 1024)).toBe("5.0 MB");
  });

  it("formats gigabytes", () => {
    expect(formatFileSize(3 * 1024 * 1024 * 1024)).toBe("3.0 GB");
  });

  it("handles fractional sizes", () => {
    expect(formatFileSize(1536)).toBe("1.5 KB");
  });
});

describe("truncate", () => {
  it("returns full string when shorter than limit", () => {
    expect(truncate("hello", 10)).toBe("hello");
  });

  it("truncates and adds ellipsis", () => {
    expect(truncate("hello world this is long", 10)).toBe("hello worl...");
  });

  it("handles empty string", () => {
    expect(truncate("", 5)).toBe("");
  });

  it("handles exact length match", () => {
    expect(truncate("12345", 5)).toBe("12345");
  });
});

describe("getFileIcon", () => {
  it("returns file-text for PDF", () => {
    expect(getFileIcon("pdf")).toBe("file-text");
  });

  it("returns file-text for DOCX", () => {
    expect(getFileIcon("docx")).toBe("file-text");
  });

  it("returns file-text for DOC", () => {
    expect(getFileIcon("doc")).toBe("file-text");
  });

  it("returns file-text for TXT", () => {
    expect(getFileIcon("txt")).toBe("file-text");
  });

  it("returns file for unknown type", () => {
    expect(getFileIcon("png")).toBe("file");
  });

  it("handles uppercase file types", () => {
    expect(getFileIcon("PDF")).toBe("file-text");
  });
});

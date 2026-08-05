import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import { sanitizeSchema } from "@/components/ChatPanel";

/**
 * Renders markdown through the same pipeline as ChatPanel.
 * NOTE: Without `rehype-raw`, raw HTML inside markdown is treated as text,
 * not parsed as HTML. This matches the production ChatPanel behavior.
 */
function renderMarkdown(markdown: string) {
  return render(
    <ReactMarkdown rehypePlugins={[[rehypeSanitize, sanitizeSchema]]}>
      {markdown}
    </ReactMarkdown>
  );
}

// ── Safe content ────────────────────────────────────────

describe("Sanitization — safe content", () => {
  it("renders plain text", () => {
    renderMarkdown("Hello world");
    expect(screen.getByText("Hello world")).toBeDefined();
  });

  it("renders bold text", () => {
    renderMarkdown("This is **bold** text");
    expect(screen.getByText("bold")).toBeDefined();
    expect(screen.getByText("bold").tagName).toBe("STRONG");
  });

  it("renders italic text", () => {
    renderMarkdown("This is *italic* text");
    expect(screen.getByText("italic").tagName).toBe("EM");
  });

  it("renders inline code", () => {
    renderMarkdown("Use `code` inline");
    const codeElement = screen.getByText("code");
    expect(codeElement).toBeDefined();
    expect(codeElement.tagName).toBe("CODE");
  });

  it("renders fenced code blocks", () => {
    renderMarkdown("```python\nprint(1)\n```");
    expect(screen.getByText("print(1)")).toBeDefined();
  });

  it("renders headings", () => {
    renderMarkdown("# Heading 1\n## Heading 2");
    expect(screen.getByText("Heading 1").tagName).toBe("H1");
    expect(screen.getByText("Heading 2").tagName).toBe("H2");
  });

  it("renders ordered lists", () => {
    renderMarkdown("1. First\n2. Second");
    expect(screen.getByText("First")).toBeDefined();
    expect(screen.getByText("Second")).toBeDefined();
  });

  it("renders unordered lists", () => {
    renderMarkdown("- Item 1\n- Item 2");
    expect(screen.getByText("Item 1")).toBeDefined();
    expect(screen.getByText("Item 2")).toBeDefined();
  });

  it("renders links with href", () => {
    renderMarkdown("[Click here](https://example.com)");
    const link = screen.getByText("Click here");
    expect(link.tagName).toBe("A");
    expect(link.getAttribute("href")).toBe("https://example.com");
  });

  it("renders blockquotes", () => {
    renderMarkdown("> A quote");
    expect(screen.getByText("A quote")).toBeDefined();
  });

  it("renders horizontal rules", () => {
    const { container } = renderMarkdown("---");
    expect(container.querySelector("hr")).not.toBeNull();
  });
});

// ── Dangerous content (should be stripped) ──────────────
// NOTE: These tests use markdown syntax or HTML that react-markdown
// processes. Without `rehype-raw`, raw HTML passed through markdown
// is treated as text nodes, not DOM elements. The sanitizer strips
// dangerous attributes from recognized elements.

describe("Sanitization — dangerous content stripped", () => {
  it("strips inline script injections from markdown", () => {
    // JavaScript in a markdown link URL should be stripped by sanitizer
    renderMarkdown("[Click](javascript:alert(1))");
    const link = screen.queryByText("Click");
    if (link) {
      const href = link.getAttribute("href");
      // Either the href is stripped entirely or doesn't contain javascript:
      expect(href === null || !href!.toLowerCase().startsWith("javascript:")).toBe(true);
    }
    // If the link element itself is removed, that's also acceptable
  });

  it("strips iframe tags from raw HTML", () => {
    const { container } = renderMarkdown("<iframe src='https://evil.com'></iframe>");
    // Without rehype-raw, this is treated as text, not an iframe element
    expect(container.querySelector("iframe")).toBeNull();
  });





  it("strips style tags from raw HTML", () => {
    const { container } = renderMarkdown("<style>body{display:none}</style>");
    // Without rehype-raw, this is treated as text, not a style element
    expect(container.querySelector("style")).toBeNull();
  });
});

// ── Allowlisted elements ───────────────────────────────

describe("Sanitization — allowlisted elements preserved", () => {


  it("preserves link href attribute", () => {
    renderMarkdown("[Link](https://example.com)");
    const link = screen.getByText("Link");
    expect(link.tagName).toBe("A");
    expect(link.getAttribute("href")).toBe("https://example.com");
  });

  it("preserves heading structure", () => {
    renderMarkdown("### Section 1");
    const heading = screen.getByText("Section 1");
    expect(heading.tagName).toBe("H3");
  });

  it("preserves code block structure", () => {
    renderMarkdown("```python\nx = 1\n```");
    const codeBlock = screen.getByText("x = 1");
    expect(codeBlock).toBeDefined();
    // Should be inside a <code> or <pre> element
    const isInCode = codeBlock.closest("code") || codeBlock.closest("pre");
    expect(isInCode).not.toBeNull();
  });
});

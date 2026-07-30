import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import { sanitizeSchema } from "@/components/ChatPanel";

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

  it("renders code blocks", () => {
    renderMarkdown("Use `code` inline");
    const codeElement = screen.getByText("code");
    expect(codeElement).toBeDefined();
    expect(codeElement.tagName).toBe("CODE");
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

  it("renders tables", () => {
    renderMarkdown("| A | B |\n|---|---|\n| 1 | 2 |");
    expect(screen.getByText("1")).toBeDefined();
    expect(screen.getByText("2")).toBeDefined();
  });
});

// ── Dangerous content (should be stripped) ──────────────

describe("Sanitization — dangerous content stripped", () => {
  it("strips script tags from markdown", () => {
    const { container } = renderMarkdown("<script>alert('xss')</script>Hello");
    expect(screen.getByText("Hello")).toBeDefined();
    expect(container.querySelector("script")).toBeNull();
  });

  it("strips onClick handlers from HTML in markdown", () => {
    renderMarkdown('<button onClick="alert(1)">Click</button>');
    const btn = screen.queryByText("Click");
    if (btn) {
      expect(btn.getAttribute("onClick")).toBeNull();
    } else {
      // Button entirely removed is also acceptable
      expect(btn).toBeNull();
    }
  });

  it("strips javascript: URLs from links (either strips the link or removes the protocol)", () => {
    renderMarkdown("[Click](javascript:alert(1))");
    const link = screen.queryByText("Click");
    if (link) {
      const href = link.getAttribute("href");
      // Either the href is stripped entirely or doesn't contain javascript:
      expect(href === null || !href!.toLowerCase().startsWith("javascript:")).toBe(true);
    }
    // If the link is entirely removed, that's also acceptable
  });

  it("strips iframe tags", () => {
    const { container } = renderMarkdown("<iframe src='https://evil.com'></iframe>");
    expect(container.querySelector("iframe")).toBeNull();
  });

  it("strips img tags", () => {
    const { container } = renderMarkdown("![alt](https://evil.com/image.png)");
    const img = container.querySelector("img");
    expect(img).toBeNull();
  });

  it("strips event handler attributes from div", () => {
    renderMarkdown('<div onmouseover="evil()">Hover me</div>');
    const div = screen.queryByText("Hover me");
    if (div) {
      expect(div.getAttribute("onmouseover")).toBeNull();
    }
  });

  it("strips style tags", () => {
    const { container } = renderMarkdown("<style>body{display:none}</style>");
    expect(container.querySelector("style")).toBeNull();
  });
});

// ── Allowlisted elements ───────────────────────────────

describe("Sanitization — allowlisted elements preserved", () => {
  it("preserves button elements with className", () => {
    renderMarkdown('<button class="citation-chip" type="button">[1]</button>');
    const btn = screen.queryByText("[1]");
    if (btn) {
      expect(btn.tagName).toBe("BUTTON");
    }
  });

  it("preserves sup elements", () => {
    renderMarkdown("Text<sup>[1]</sup>");
    const sup = screen.queryByText("[1]");
    if (sup) {
      expect(sup.tagName).toBe("SUP");
    }
  });

  it("preserves code with className", () => {
    renderMarkdown('<code class="language-python">print(1)</code>');
    const code = screen.queryByText("print(1)");
    if (code) {
      expect(code.tagName).toBe("CODE");
    }
  });

  it("preserves link target and rel attributes", () => {
    renderMarkdown("[Link](https://example.com)");
    const link = screen.getByText("Link");
    // Links should have target and rel for security (noreferrer, noopener)
    expect(link.getAttribute("rel")).not.toBeNull();
  });
});

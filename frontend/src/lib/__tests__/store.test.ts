import { describe, it, expect, beforeEach } from "vitest";
import { useChatStore, useDocumentStore } from "@/lib/store";

beforeEach(() => {
  useChatStore.getState().resetStreaming();
});

describe("useChatStore", () => {
  it("starts with empty streaming content", () => {
    expect(useChatStore.getState().streamingContent).toBe("");
    expect(useChatStore.getState().isStreaming).toBe(false);
  });

  it("sets streaming content", () => {
    useChatStore.getState().setStreamingContent("Hello");
    expect(useChatStore.getState().streamingContent).toBe("Hello");
  });

  it("appends tokens", () => {
    useChatStore.getState().appendToken("Hello ");
    useChatStore.getState().appendToken("World");
    expect(useChatStore.getState().streamingContent).toBe("Hello World");
  });

  it("sets streaming state", () => {
    useChatStore.getState().setStreaming(true);
    expect(useChatStore.getState().isStreaming).toBe(true);
    useChatStore.getState().setStreaming(false);
    expect(useChatStore.getState().isStreaming).toBe(false);
  });

  it("resets streaming state", () => {
    useChatStore.getState().appendToken("Some content");
    useChatStore.getState().setStreaming(true);
    useChatStore.getState().resetStreaming();
    expect(useChatStore.getState().streamingContent).toBe("");
    expect(useChatStore.getState().isStreaming).toBe(false);
  });
});

describe("useDocumentStore", () => {
  it("starts with no selected document", () => {
    expect(useDocumentStore.getState().selectedDocumentId).toBeNull();
  });

  it("sets selected document", () => {
    useDocumentStore.getState().setSelectedDocument("doc-123");
    expect(useDocumentStore.getState().selectedDocumentId).toBe("doc-123");
  });

  it("clears selected document", () => {
    useDocumentStore.getState().setSelectedDocument("doc-123");
    useDocumentStore.getState().setSelectedDocument(null);
    expect(useDocumentStore.getState().selectedDocumentId).toBeNull();
  });
});

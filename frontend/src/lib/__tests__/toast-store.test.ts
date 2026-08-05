import { describe, it, expect, beforeEach } from "vitest";
import { useToastStore, toast } from "@/lib/toast-store";

beforeEach(() => {
  useToastStore.getState().clearToasts();
});

describe("useToastStore", () => {
  it("starts with empty toasts", () => {
    expect(useToastStore.getState().toasts).toEqual([]);
  });

  it("adds a toast", () => {
    const id = useToastStore.getState().addToast({
      type: "success",
      title: "Done!",
    });
    expect(id).toBeTruthy();
    expect(useToastStore.getState().toasts).toHaveLength(1);
    expect(useToastStore.getState().toasts[0].title).toBe("Done!");
    expect(useToastStore.getState().toasts[0].type).toBe("success");
  });

  it("adds a toast with message", () => {
    useToastStore.getState().addToast({
      type: "error",
      title: "Failed",
      message: "Something went wrong",
    });
    const t = useToastStore.getState().toasts[0];
    expect(t.message).toBe("Something went wrong");
  });

  it("removes a toast by id", () => {
    const id = useToastStore.getState().addToast({
      type: "info",
      title: "Test",
    });
    expect(useToastStore.getState().toasts).toHaveLength(1);
    useToastStore.getState().removeToast(id);
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });

  it("clears all toasts", () => {
    useToastStore.getState().addToast({ type: "info", title: "A" });
    useToastStore.getState().addToast({ type: "warning", title: "B" });
    expect(useToastStore.getState().toasts).toHaveLength(2);
    useToastStore.getState().clearToasts();
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });

  it("generates unique ids for each toast", () => {
    const id1 = useToastStore.getState().addToast({ type: "success", title: "1" });
    const id2 = useToastStore.getState().addToast({ type: "error", title: "2" });
    expect(id1).not.toBe(id2);
  });
});

describe("toast helper", () => {
  it("toast.success adds a success toast", () => {
    toast.success("Success!");
    const t = useToastStore.getState().toasts[0];
    expect(t.type).toBe("success");
    expect(t.title).toBe("Success!");
  });

  it("toast.error adds an error toast", () => {
    toast.error("Error!", "Details");
    const t = useToastStore.getState().toasts[0];
    expect(t.type).toBe("error");
    expect(t.title).toBe("Error!");
    expect(t.message).toBe("Details");
  });

  it("toast.info adds an info toast", () => {
    toast.info("Info");
    const t = useToastStore.getState().toasts[0];
    expect(t.type).toBe("info");
  });

  it("toast.warning adds a warning toast", () => {
    toast.warning("Warn");
    const t = useToastStore.getState().toasts[0];
    expect(t.type).toBe("warning");
  });
});

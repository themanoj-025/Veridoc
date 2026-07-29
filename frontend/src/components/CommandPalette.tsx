"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/lib/store";
import { useDocumentStore } from "@/lib/store";

interface Command {
  id: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  action: () => void;
  keywords: string[];
}

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const logout = useAuthStore((s) => s.logout);
  const { toggleDarkMode } = useDocumentStore();

  // Toggle dark mode helper
  const toggleTheme = useCallback(() => {
    const isDark = document.documentElement.classList.contains("dark");
    const next = isDark ? "light" : "dark";
    document.documentElement.classList.toggle("dark", !isDark);
    localStorage.setItem("theme", next);
  }, []);

  const commands: Command[] = [
    {
      id: "new-chat",
      label: "New Conversation",
      description: "Start a new chat conversation",
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
        </svg>
      ),
      action: () => {
        // Dispatch custom event for the dashboard to handle
        window.dispatchEvent(new CustomEvent("command-new-chat"));
        setOpen(false);
      },
      keywords: ["new", "chat", "conversation", "start", "create"],
    },
    {
      id: "toggle-theme",
      label: "Toggle Dark Mode",
      description: "Switch between light and dark theme",
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
        </svg>
      ),
      action: () => {
        toggleTheme();
        setOpen(false);
      },
      keywords: ["dark", "light", "theme", "mode", "toggle", "switch"],
    },
    {
      id: "upload-doc",
      label: "Upload Document",
      description: "Upload a PDF, DOCX, or TXT file",
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
      ),
      action: () => {
        window.dispatchEvent(new CustomEvent("command-upload-doc"));
        setOpen(false);
      },
      keywords: ["upload", "document", "file", "pdf", "docx", "txt"],
    },
    {
      id: "search-docs",
      label: "Search Documents",
      description: "Search across all your documents",
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      ),
      action: () => {
        window.dispatchEvent(new CustomEvent("command-search"));
        setOpen(false);
      },
      keywords: ["search", "find", "document", "lookup", "query"],
    },
    {
      id: "sign-out",
      label: "Sign Out",
      description: "Log out of your account",
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
        </svg>
      ),
      action: () => {
        logout();
        router.push("/login");
        setOpen(false);
      },
      keywords: ["sign", "out", "logout", "exit", "leave"],
    },
  ];

  // Filter commands based on query
  const filtered = query
    ? commands.filter(
        (cmd) =>
          cmd.label.toLowerCase().includes(query.toLowerCase()) ||
          cmd.keywords.some((k) => k.includes(query.toLowerCase()))
      )
    : commands;

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
        setQuery("");
        setSelectedIndex(0);
      }
      if (e.key === "Escape" && open) {
        setOpen(false);
        setQuery("");
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open]);

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, filtered.length - 1));
        break;
      case "ArrowUp":
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
        break;
      case "Enter":
        e.preventDefault();
        if (filtered[selectedIndex]) {
          filtered[selectedIndex].action();
        }
        break;
    }
  };

  if (!open) return null;

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
        onClick={() => setOpen(false)}
      />

      {/* Palette */}
      <div
        className="fixed top-[15%] left-1/2 -translate-x-1/2 z-50 w-full max-w-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="bg-card border border-border rounded-2xl shadow-2xl overflow-hidden animate-scale-in">
          {/* Search input */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-border">
            <svg className="w-5 h-5 text-muted-foreground shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setSelectedIndex(0);
              }}
              onKeyDown={handleKeyDown}
              placeholder="Search commands..."
              className="flex-1 bg-transparent text-foreground placeholder-muted-foreground outline-none text-sm"
            />
            <kbd className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-muted text-xs text-muted-foreground font-mono">
              ESC
            </kbd>
          </div>

          {/* Results */}
          <div className="max-h-80 overflow-y-auto p-2">
            {filtered.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-sm text-muted-foreground">No results found</p>
              </div>
            ) : (
              <div className="space-y-1">
                {filtered.map((cmd, index) => (
                  <button
                    key={cmd.id}
                    onClick={cmd.action}
                    className={cn(
                      "w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-colors",
                      index === selectedIndex
                        ? "bg-veridoc-50 dark:bg-veridoc-900/30 text-foreground"
                        : "text-muted-foreground hover:bg-surface-hover hover:text-foreground"
                    )}
                    onMouseEnter={() => setSelectedIndex(index)}
                  >
                    <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center shrink-0">
                      {cmd.icon}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-foreground">{cmd.label}</p>
                      <p className="text-xs text-muted-foreground">{cmd.description}</p>
                    </div>
                    {index === selectedIndex && (
                      <kbd className="hidden sm:inline-flex items-center px-1.5 py-0.5 rounded bg-muted text-xs text-muted-foreground font-mono">
                        ↵
                      </kbd>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Footer hint */}
          <div className="px-4 py-2 border-t border-border bg-muted/50">
            <p className="text-xs text-muted-foreground">
              Press <kbd className="px-1 py-0.5 rounded bg-background font-mono">↑</kbd>{" "}
              <kbd className="px-1 py-0.5 rounded bg-background font-mono">↓</kbd> to navigate,{" "}
              <kbd className="px-1 py-0.5 rounded bg-background font-mono">↵</kbd> to select
            </p>
          </div>
        </div>
      </div>
    </>
  );
}

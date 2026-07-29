"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

interface SearchResult {
  id: string;
  title: string;
  type: "document" | "conversation";
  subtitle?: string;
}

interface SearchBarProps {
  documents: { id: string; title: string; filename: string }[];
  conversations: { id: string; title: string }[];
  onSelectDocument: (id: string) => void;
  onSelectConversation: (id: string) => void;
  onFullTextSearch?: (query: string) => void;
  className?: string;
}

export function SearchBar({
  documents,
  conversations,
  onSelectDocument,
  onSelectConversation,
  onFullTextSearch,
  className,
}: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Filter results
  const results: SearchResult[] = [];
  if (query.trim()) {
    const q = query.toLowerCase();
    documents
      .filter((d) => d.title.toLowerCase().includes(q) || d.filename.toLowerCase().includes(q))
      .forEach((d) =>
        results.push({
          id: d.id,
          title: d.title,
          type: "document",
          subtitle: d.filename,
        })
      );
    conversations
      .filter((c) => c.title.toLowerCase().includes(q))
      .forEach((c) =>
        results.push({
          id: c.id,
          title: c.title,
          type: "conversation",
        })
      );
  }

  const showResults = isOpen && query.trim().length > 0;

  const handleSelect = useCallback(
    (result: SearchResult) => {
      if (result.type === "document") {
        onSelectDocument(result.id);
      } else {
        onSelectConversation(result.id);
      }
      setQuery("");
      setIsOpen(false);
    },
    [onSelectDocument, onSelectConversation]
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, results.length - 1));
        break;
      case "ArrowUp":
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
        break;
      case "Enter":
        e.preventDefault();
        if (results[selectedIndex]) {
          handleSelect(results[selectedIndex]);
        } else if (query.trim() && onFullTextSearch) {
          onFullTextSearch(query.trim());
          setQuery("");
          setIsOpen(false);
        }
        break;
      case "Escape":
        setIsOpen(false);
        break;
    }
  };

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      {/* Search input */}
      <div className="relative">
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
            setSelectedIndex(0);
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder="Search documents & conversations..."
          className="w-full pl-10 pr-4 py-2 rounded-xl border border-input bg-background text-sm
                     focus:outline-none focus:ring-2 focus:ring-veridoc-500/20 focus:border-veridoc-500
                     transition-all duration-150 placeholder:text-muted-foreground/60"
        />
        {query && (
          <button
            onClick={() => {
              setQuery("");
              setIsOpen(false);
            }}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Results dropdown */}
      {showResults && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-card border border-border rounded-xl shadow-xl overflow-hidden z-30 animate-scale-in">
          {results.length === 0 ? (
            <div className="p-4 text-center">
              <p className="text-sm text-muted-foreground">No results found</p>
              {onFullTextSearch && (
                <button
                  onClick={() => {
                    onFullTextSearch(query.trim());
                    setQuery("");
                    setIsOpen(false);
                  }}
                  className="mt-2 text-sm text-veridoc-500 hover:text-veridoc-600 font-medium"
                >
                  Search inside documents for &ldquo;{query}&rdquo;
                </button>
              )}
            </div>
          ) : (
            <div className="max-h-80 overflow-y-auto p-1">
              {results.map((result, index) => (
                <button
                  key={`${result.type}-${result.id}`}
                  onClick={() => handleSelect(result)}
                  className={cn(
                    "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors",
                    index === selectedIndex
                      ? "bg-veridoc-50 dark:bg-veridoc-900/30"
                      : "hover:bg-surface-hover"
                  )}
                  onMouseEnter={() => setSelectedIndex(index)}
                >
                  <div
                    className={cn(
                      "w-8 h-8 rounded-lg flex items-center justify-center shrink-0",
                      result.type === "document"
                        ? "bg-veridoc-100 text-veridoc-600 dark:bg-veridoc-900/50 dark:text-veridoc-400"
                        : "bg-secondary text-muted-foreground"
                    )}
                  >
                    {result.type === "document" ? (
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    ) : (
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                      </svg>
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-foreground truncate">
                      {result.title}
                    </p>
                    <p className="text-xs text-muted-foreground capitalize">
                      {result.type}{result.subtitle && ` · ${result.subtitle}`}
                    </p>
                  </div>
                  <kbd className="hidden sm:inline-flex items-center px-1.5 py-0.5 rounded bg-muted text-xs text-muted-foreground font-mono">
                    {index + 1}
                  </kbd>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

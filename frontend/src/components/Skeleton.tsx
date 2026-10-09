"use client";

import { cn } from "@/lib/utils";

interface SkeletonProps {
  className?: string;
}

/**
 * Base skeleton component with shimmer animation.
 * Use the composed variants below for common use cases.
 */
export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded bg-muted animate-pulse",
        className
      )}
      aria-hidden="true"
    />
  );
}

/* ── Composed Skeleton Variants ── */

/** Document list item skeleton */
export function DocumentListSkeleton() {
  return (
    <div className="p-3 space-y-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="flex items-start gap-3 p-3 rounded-xl">
          <Skeleton className="w-8 h-8 rounded-lg shrink-0" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
            <Skeleton className="h-3 w-1/4" />
          </div>
        </div>
      ))}
    </div>
  );
}

/** Chat message skeleton (assistant response) */
export function ChatMessageSkeleton() {
  return (
    <div className="space-y-3">
      <div className="flex justify-start">
        <div className="max-w-[85%] rounded-2xl px-4 py-3 bg-secondary">
          <Skeleton className="h-4 w-3/4 mb-2" />
          <Skeleton className="h-4 w-full mb-2" />
          <Skeleton className="h-4 w-2/3 mb-2" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      </div>
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl px-4 py-3 bg-veridoc-100">
          <Skeleton className="h-4 w-1/2" />
        </div>
      </div>
    </div>
  );
}

/** Empty state skeleton shown when loading conversations */
export function ConversationListSkeleton() {
  return (
    <div className="space-y-1 p-2">
      {Array.from({ length: 3 }).map((_, i) => (
        <Skeleton key={i} className="h-8 w-full rounded-lg" />
      ))}
    </div>
  );
}

/** Document viewer content skeleton */
export function DocumentViewerSkeleton() {
  return (
    <div className="p-6 space-y-4">
      <Skeleton className="h-6 w-1/2" />
      <Skeleton className="h-4 w-1/4" />
      <div className="p-4 rounded-xl bg-veridoc-50/50 space-y-3 mt-6">
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-3 w-1/2" />
        <Skeleton className="h-3 w-2/3" />
        <Skeleton className="h-3 w-1/2" />
      </div>
      <div className="space-y-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-3 w-full" />
        ))}
      </div>
    </div>
  );
}

/** Upload modal processing skeleton */
export function UploadProgressSkeleton({ progress }: { progress?: number }) {
  return (
    <div className="space-y-3 p-4">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-veridoc-100 flex items-center justify-center">
          <svg className="w-4 h-4 text-veridoc-500 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        </div>
        <div className="flex-1">
          <div className="flex justify-between mb-1">
            <span className="text-sm font-medium text-foreground">Processing...</span>
            <span className="text-xs text-muted-foreground">{progress ?? 0}%</span>
          </div>
          <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-veridoc-500 rounded-full transition-all duration-500"
              style={{ width: `${progress ?? 0}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

/** Ingestion status skeleton (for document processing states) */
export function IngestionSkeleton() {
  const stages = ["Parsing...", "Chunking...", "Embedding...", "Indexing..."];
  return (
    <div className="space-y-3 p-4">
      {stages.map((stage, i) => (
        <div key={i} className="flex items-center gap-3 animate-fade-in-up" style={{ animationDelay: `${i * 200}ms` }}>
          <div className={cn(
            "w-5 h-5 rounded-full border-2 flex items-center justify-center",
            "border-muted-foreground/30"
          )}>
            <div className="w-2 h-2 rounded-full bg-muted-foreground/20" />
          </div>
          <div className="flex-1">
            <Skeleton className="h-3 w-24" />
          </div>
        </div>
      ))}
    </div>
  );
}

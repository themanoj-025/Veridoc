"use client";

import { cn } from "@/lib/utils";

interface OCRBadgeProps {
  ocrUsed: boolean;
  size?: "sm" | "xs";
  className?: string;
}

/**
 * A small badge indicating whether a chunk was extracted via OCR.
 *
 * - When ``ocrUsed`` is true, renders an "OCR-extracted" badge with a
 *   distinct camera icon and orange/amber color.
 * - When ``ocrUsed`` is false, renders nothing (returns null).
 *
 * Use this in ``DocumentViewer`` next to page/section headers and in
 * ``ChatPanel`` citation chips to provide source transparency for
 * OCR-originated content.
 */
export function OCRBadge({ ocrUsed, size = "xs", className }: OCRBadgeProps) {
  if (!ocrUsed) return null;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded font-medium",
        "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
        "border border-amber-200 dark:border-amber-800/40",
        size === "xs"
          ? "px-1.5 py-0.5 text-[10px]"
          : "px-2 py-0.5 text-xs",
        className
      )}
      title="This content was extracted using OCR (optical character recognition)"
      aria-label="OCR extracted content"
    >
      {/* Camera icon */}
      <svg
        className={cn(size === "xs" ? "w-2.5 h-2.5" : "w-3 h-3")}
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
        />
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"
        />
      </svg>
      OCR
    </span>
  );
}

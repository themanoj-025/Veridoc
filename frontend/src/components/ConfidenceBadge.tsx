"use client";

import { cn } from "@/lib/utils";

interface ConfidenceBadgeProps {
  retrievalScore?: number | null;
  faithfulnessScore?: number | null;
  className?: string;
  size?: "sm" | "xs";
}

type ConfidenceLevel = "high" | "medium" | "low";

/**
 * G1: Per-answer confidence indicator combining retrieval and faithfulness scores.
 *
 * - **High** (green): Both scores >= 0.8
 * - **Medium** (amber): Both scores >= 0.5 OR one >= 0.8 and one >= 0.5
 * - **Low** (red): Either score < 0.5 or both are missing/null
 *
 * Renders a small badge with icon, label, and a color indicator.
 * Distinct from the OCR badge — this surfaces answer-level trust, not source type.
 */
export function ConfidenceBadge({
  retrievalScore,
  faithfulnessScore,
  className,
  size = "xs",
}: ConfidenceBadgeProps) {
  const level = getConfidenceLevel(retrievalScore, faithfulnessScore);

  const config = {
    high: {
      label: "High confidence",
      bg: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
      border: "border-green-200 dark:border-green-800/40",
      dot: "bg-green-500",
    },
    medium: {
      label: "Medium confidence",
      bg: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
      border: "border-amber-200 dark:border-amber-800/40",
      dot: "bg-amber-400",
    },
    low: {
      label: "Low confidence",
      bg: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
      border: "border-red-200 dark:border-red-800/40",
      dot: "bg-red-500",
    },
  }[level];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded font-medium border",
        config.bg,
        config.border,
        size === "xs" ? "px-1.5 py-0.5 text-[10px]" : "px-2 py-0.5 text-xs",
        className,
      )}
      title={`${config.label} (retrieval: ${retrievalScore?.toFixed(2) ?? "N/A"}, faithfulness: ${faithfulnessScore?.toFixed(2) ?? "N/A"})`}
      aria-label={`Answer confidence: ${level}`}
    >
      <span className={cn("w-1.5 h-1.5 rounded-full", config.dot)} />
      {config.label}
    </span>
  );
}

function getConfidenceLevel(
  retrievalScore?: number | null,
  faithfulnessScore?: number | null,
): ConfidenceLevel {
  const r = retrievalScore ?? null;
  const f = faithfulnessScore ?? null;

  // If both are missing, default to low
  if (r === null && f === null) return "low";

  const rVal = r ?? 0;
  const fVal = f ?? 0;

  // High: both >= 0.8
  if (rVal >= 0.8 && fVal >= 0.8) return "high";

  // Low: either < 0.5
  if (rVal < 0.5 || fVal < 0.5) return "low";

  // Medium: everything else (both between 0.5 and 0.8, or one >= 0.8 and the other >= 0.5)
  return "medium";
}

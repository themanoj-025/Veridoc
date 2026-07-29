"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { useToastStore } from "@/lib/toast-store";

interface ThumbsUpDownProps {
  messageId: string;
  conversationId: string;
  question: string;
  answer: string;
  citations?: any[];
  faithfulnessScore?: number | null;
}

export function ThumbsUpDown({
  messageId,
  conversationId,
  question,
  answer,
  citations,
  faithfulnessScore,
}: ThumbsUpDownProps) {
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleFeedback = async (type: "up" | "down") => {
    if (submitting || feedback === type) return;
    setSubmitting(true);

    try {
      // Send feedback to API
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/chat/feedback`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
          body: JSON.stringify({
            message_id: messageId,
            conversation_id: conversationId,
            feedback: type,
            question,
            answer,
            citations,
            faithfulness_score: faithfulnessScore,
          }),
        }
      );

      if (response.ok) {
        setFeedback(type);
        if (type === "down") {
          useToastStore.getState().addToast({
            type: "info",
            title: "Feedback recorded",
            message: "This will help improve future responses.",
          });
        } else {
          useToastStore.getState().addToast({
            type: "success",
            title: "Thanks for your feedback!",
          });
        }
      }
    } catch {
      // Silently fail - feedback is non-critical
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex items-center gap-1.5 mt-2 pt-2 border-t border-border/50">
      <span className="text-xs text-muted-foreground">Was this helpful?</span>
      <button
        onClick={() => handleFeedback("up")}
        disabled={submitting}
        className={cn(
          "p-1 rounded-md transition-all duration-150",
          "text-muted-foreground hover:text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20",
          feedback === "up" && "text-green-600 bg-green-50 dark:bg-green-900/20 dark:text-green-400",
          "disabled:opacity-50"
        )}
        aria-label="Thumbs up"
        title="Helpful"
      >
        <svg className="w-4 h-4" fill={feedback === "up" ? "currentColor" : "none"} viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
        </svg>
      </button>
      <button
        onClick={() => handleFeedback("down")}
        disabled={submitting}
        className={cn(
          "p-1 rounded-md transition-all duration-150",
          "text-muted-foreground hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20",
          feedback === "down" && "text-red-600 bg-red-50 dark:bg-red-900/20 dark:text-red-400",
          "disabled:opacity-50"
        )}
        aria-label="Thumbs down"
        title="Not helpful"
      >
        <svg className="w-4 h-4" fill={feedback === "down" ? "currentColor" : "none"} viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
        </svg>
      </button>
    </div>
  );
}

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import {
  useAdminAnalytics,
  useAdminCacheStats,
  useAdminFeedbackQueue,
} from "@/lib/queries";

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-card border border-border rounded-xl p-4">
      <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold text-foreground mt-1">{value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
    </div>
  );
}

export default function AdminPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuthStore();
  const [activeSection, setActiveSection] = useState<"analytics" | "cache" | "feedback">("analytics");

  // ▸ F14: Admin data served by React Query
  const {
    data: analyticsData,
    isError: analyticsError,
    isLoading: loadingAnalytics,
    refetch: refetchAnalytics,
  } = useAdminAnalytics();
  const {
    data: cacheStats,
    isLoading: loadingCache,
    refetch: refetchCache,
  } = useAdminCacheStats();
  const {
    data: feedbackStats,
    isLoading: loadingFeedback,
    refetch: refetchFeedback,
  } = useAdminFeedbackQueue();

  const loading = loadingAnalytics || loadingCache || loadingFeedback;
  const error = analyticsData === null && !loadingAnalytics
    ? "Admin access required (only the first registered user can access this page)"
    : analyticsError
      ? "Failed to load admin data"
      : null;

  const refreshAll = () => {
    refetchAnalytics();
    refetchCache();
    refetchFeedback();
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 rounded-full bg-veridoc-500 animate-pulse" />
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="h-14 border-b bg-card/80 backdrop-blur-sm flex items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/dashboard")}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
          </button>
          <div className="w-8 h-8 rounded-lg bg-veridoc-500 flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <span className="font-semibold text-foreground">Admin Analytics</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => router.push("/dashboard")}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Dashboard
          </button>
          <button
            onClick={refreshAll}
            className="text-sm text-veridoc-500 hover:text-veridoc-600 font-medium"
          >
            Refresh
          </button>
        </div>
      </header>

      {/* Section tabs */}
      <div className="border-b bg-card/50 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto flex gap-1 px-4">
          {[
            { id: "analytics" as const, label: "Analytics" },
            { id: "cache" as const, label: "Cache Stats" },
            { id: "feedback" as const, label: "Feedback Queue" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveSection(tab.id)}
              className={cn(
                "px-4 py-3 text-sm font-medium border-b-2 transition-colors",
                activeSection === tab.id
                  ? "border-veridoc-500 text-veridoc-600"
                  : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="max-w-6xl mx-auto p-6">
        {error && (
          <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm mb-6">
            {error}
            <button
              onClick={() => router.push("/dashboard")}
              className="ml-2 underline font-medium"
            >
              Back to dashboard
            </button>
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 rounded-full border-2 border-veridoc-200 border-t-veridoc-500 animate-spin" />
              <p className="text-sm text-muted-foreground">Loading admin data...</p>
            </div>
          </div>
        )}

        {/* Analytics Section */}
        {analyticsData && activeSection === "analytics" && (
          <div className="space-y-8">
            {/* Stats grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="Total Queries" value={analyticsData.total_queries} />
              <StatCard label="Total Users" value={analyticsData.total_users} />
              <StatCard label="Total Documents" value={analyticsData.total_documents} />
              <StatCard label="Avg Latency" value={`${analyticsData.avg_latency_ms.toFixed(0)}ms`} />
              <StatCard label="P50 Latency" value={`${analyticsData.p50_latency_ms.toFixed(0)}ms`} />
              <StatCard label="P95 Latency" value={`${analyticsData.p95_latency_ms.toFixed(0)}ms`} />
              <StatCard label="Queries Today" value={analyticsData.queries_today} />
              <StatCard label="Queries (7d)" value={analyticsData.queries_this_week} />
              <StatCard label="Most Used Model" value={analyticsData.most_used_model || "N/A"} />
              <StatCard
                label="Avg Cost/Query"
                value={analyticsData.avg_estimated_cost ? `$${analyticsData.avg_estimated_cost.toFixed(6)}` : "N/A"}
              />
            </div>

            {/* Daily volume */}
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-3">Daily Query Volume (7 days)</h3>
              <div className="flex items-end gap-2 h-32">
                {(analyticsData.daily_query_volume?.length > 0 ? analyticsData.daily_query_volume : []).map((day) => {
                  const maxCount = Math.max(...(analyticsData.daily_query_volume?.map((d) => d.count) || [1]), 1);
                  const height = (day.count / maxCount) * 100;
                  return (
                    <div key={day.date} className="flex-1 flex flex-col items-center gap-1">
                      <span className="text-xs text-muted-foreground">{day.count}</span>
                      <div
                        className="w-full bg-veridoc-500 rounded-t transition-all duration-300"
                        style={{ height: `${height}%`, minHeight: day.count > 0 ? "4px" : "0" }}
                      />
                      <span className="text-xs text-muted-foreground">
                        {new Date(day.date).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Recent queries */}
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-3">Recent Queries</h3>
              <div className="border border-border rounded-xl overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-muted/50">
                      <th className="text-left px-4 py-2 text-muted-foreground font-medium">Query</th>
                      <th className="text-left px-4 py-2 text-muted-foreground font-medium">Latency</th>
                      <th className="text-left px-4 py-2 text-muted-foreground font-medium">Model</th>
                      <th className="text-left px-4 py-2 text-muted-foreground font-medium">Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analyticsData.recent_queries.map((q, i) => (
                      <tr key={i} className="border-t border-border hover:bg-muted/30">
                        <td className="px-4 py-2 text-foreground max-w-xs truncate">{q.query}</td>
                        <td className="px-4 py-2 text-muted-foreground">{q.latency_ms.toFixed(0)}ms</td>
                        <td className="px-4 py-2 text-muted-foreground">{q.model_used || "N/A"}</td>
                        <td className="px-4 py-2 text-muted-foreground">
                          {q.created_at ? new Date(q.created_at).toLocaleString() : "N/A"}
                        </td>
                      </tr>
                    ))}
                    {analyticsData.recent_queries.length === 0 && (
                      <tr>
                        <td colSpan={4} className="px-4 py-8 text-center text-muted-foreground">
                          No queries yet
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Top documents */}
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-3">Most-Cited Documents</h3>
              <div className="border border-border rounded-xl overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-muted/50">
                      <th className="text-left px-4 py-2 text-muted-foreground font-medium">Document ID</th>
                      <th className="text-left px-4 py-2 text-muted-foreground font-medium">Citation Count</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analyticsData.top_documents.map((doc, i) => (
                      <tr key={i} className="border-t border-border hover:bg-muted/30">
                        <td className="px-4 py-2 text-foreground font-mono text-xs">{doc.document_id}</td>
                        <td className="px-4 py-2 text-foreground font-medium">{doc.citation_count}</td>
                      </tr>
                    ))}
                    {analyticsData.top_documents.length === 0 && (
                      <tr>
                        <td colSpan={2} className="px-4 py-8 text-center text-muted-foreground">
                          No citations yet
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Cache Stats Section (C2) */}
        {cacheStats && activeSection === "cache" && (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold text-foreground">Response Cache Statistics</h2>
            <p className="text-sm text-muted-foreground">
              Redis-backed query/response cache that stores complete LLM responses
              keyed by a hash of (conversation_id, query). Repeated questions skip
              the full retrieve → rerank → generate pipeline.
            </p>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-card border border-border rounded-xl p-4">
                <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">Status</p>
                <div className="flex items-center gap-2 mt-2">
                  <div className={cn(
                    "w-2.5 h-2.5 rounded-full",
                    cacheStats.enabled ? "bg-green-400" : "bg-red-400"
                  )} />
                  <span className="text-lg font-bold text-foreground">
                    {cacheStats.enabled ? "Active" : "Disabled"}
                  </span>
                </div>
              </div>
              <div className="bg-card border border-border rounded-xl p-4">
                <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">Storage</p>
                <div className="flex items-center gap-2 mt-2">
                  <div className={cn(
                    "w-2.5 h-2.5 rounded-full",
                    cacheStats.redis_available ? "bg-green-400" : "bg-amber-400"
                  )} />
                  <span className="text-lg font-bold text-foreground">
                    {cacheStats.redis_available ? "Redis" : "Memory"}
                  </span>
                </div>
              </div>
              <StatCard label="Cache TTL" value={`${cacheStats.ttl_seconds}s`} />
              <StatCard label="Memory Entries" value={cacheStats.memory_entries} />
            </div>

            {/* Hit rate gauge */}
            <div className="bg-card border border-border rounded-xl p-6">
              <p className="text-sm font-semibold text-foreground mb-3">Hit Rate</p>
              <div className="flex items-end gap-4">
                <div className="relative w-24 h-24">
                  <svg className="w-24 h-24 -rotate-90" viewBox="0 0 100 100">
                    <circle
                      cx="50" cy="50" r="42"
                      fill="none"
                      stroke="hsl(var(--muted))"
                      strokeWidth="8"
                    />
                    <circle
                      cx="50" cy="50" r="42"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="8"
                      strokeDasharray={`${2 * Math.PI * 42}`}
                      strokeDashoffset={`${2 * Math.PI * 42 * (1 - cacheStats.hit_rate)}`}
                      strokeLinecap="round"
                      className={cn(
                        "transition-all duration-700",
                        cacheStats.hit_rate >= 0.5 ? "text-green-500" :
                        cacheStats.hit_rate >= 0.25 ? "text-amber-500" : "text-red-500"
                      )}
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-2xl font-bold text-foreground">
                      {(cacheStats.hit_rate * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="w-16 text-muted-foreground">Hits:</span>
                    <span className="font-semibold text-foreground">{cacheStats.hits.toLocaleString()}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <span className="w-16 text-muted-foreground">Misses:</span>
                    <span className="font-semibold text-foreground">{cacheStats.misses.toLocaleString()}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <span className="w-16 text-muted-foreground">Total:</span>
                    <span className="font-semibold text-foreground">{cacheStats.total.toLocaleString()}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Feedback Queue Section (D1) */}
        {feedbackStats && activeSection === "feedback" && (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold text-foreground">Continuous Feedback Queue</h2>
            <p className="text-sm text-muted-foreground">
              Thumbs-up/down feedback submitted by users. Thumbs-down entries are
              automatically queued for review and potential promotion into the gold Q&A set.
              Run <code className="px-1 py-0.5 rounded bg-muted text-xs font-mono">python scripts/promote_feedback.py</code>
              to review and promote entries.
            </p>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="Total Entries" value={feedbackStats.total} />
              <StatCard label="Thumbs Up" value={feedbackStats.thumbs_up} />
              <StatCard label="Thumbs Down" value={feedbackStats.thumbs_down} />
              <StatCard
                label="Avg Faithfulness"
                value={`${(feedbackStats.avg_faithfulness * 100).toFixed(0)}%`}
              />
            </div>

            {feedbackStats.recent_entries.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-foreground mb-3">Recent Entries</h3>
                <div className="border border-border rounded-xl overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-muted/50">
                        <th className="text-left px-4 py-2 text-muted-foreground font-medium">Feedback</th>
                        <th className="text-left px-4 py-2 text-muted-foreground font-medium">Question</th>
                        <th className="text-left px-4 py-2 text-muted-foreground font-medium">Faithfulness</th>
                        <th className="text-left px-4 py-2 text-muted-foreground font-medium">Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {feedbackStats.recent_entries.slice(0, 10).map((entry, i) => (
                        <tr key={i} className="border-t border-border hover:bg-muted/30">
                          <td className="px-4 py-2">
                            <span className={cn(
                              "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
                              entry.feedback === "up"
                                ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                                : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                            )}>
                              {entry.feedback === "up" ? "👍 Up" : "👎 Down"}
                            </span>
                          </td>
                          <td className="px-4 py-2 text-foreground max-w-xs truncate">{entry.question}</td>
                          <td className="px-4 py-2 text-muted-foreground">
                            {entry.faithfulness_score !== null && entry.faithfulness_score !== undefined
                              ? `${(entry.faithfulness_score * 100).toFixed(0)}%`
                              : "N/A"}
                          </td>
                          <td className="px-4 py-2 text-muted-foreground text-xs">
                            {entry.timestamp
                              ? new Date(entry.timestamp).toLocaleString()
                              : "N/A"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {feedbackStats.total === 0 && (
              <div className="p-8 text-center">
                <div className="w-12 h-12 rounded-2xl bg-veridoc-100 mx-auto mb-3 flex items-center justify-center">
                  <svg className="w-6 h-6 text-veridoc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <p className="text-sm text-muted-foreground">No feedback entries yet</p>
              </div>
            )}
          </div>
        )}

        {!loading && !analyticsData && !cacheStats && !feedbackStats && !error && (
          <div className="p-8 text-center">
            <p className="text-sm text-muted-foreground">
              No data available. Start by uploading documents and asking questions.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

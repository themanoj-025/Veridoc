"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store";
import { cn } from "@/lib/utils";

interface AnalyticsData {
  total_queries: number;
  total_users: number;
  total_documents: number;
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  queries_today: number;
  queries_this_week: number;
  most_used_model: string | null;
  avg_estimated_cost: number | null;
  top_documents: { document_id: string; citation_count: number }[];
  recent_queries: { query: string; latency_ms: number; model_used: string; created_at: string | null }[];
  daily_query_volume: { date: string; count: number }[];
}

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
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  useEffect(() => {
    if (!isAuthenticated) return;
    loadAnalytics();
  }, [isAuthenticated]);

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/admin/analytics`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.status === 403) {
        setError("Admin access required (only the first registered user can access this page)");
      } else if (res.ok) {
        setData(await res.json());
      } else {
        setError(`Error ${res.status}: ${res.statusText}`);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load analytics");
    } finally {
      setLoading(false);
    }
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
        <button
          onClick={loadAnalytics}
          className="text-sm text-veridoc-500 hover:text-veridoc-600 font-medium"
        >
          Refresh
        </button>
      </header>

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
              <p className="text-sm text-muted-foreground">Loading analytics...</p>
            </div>
          </div>
        )}

        {data && (
          <div className="space-y-8">
            {/* Stats grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="Total Queries" value={data.total_queries} />
              <StatCard label="Total Users" value={data.total_users} />
              <StatCard label="Total Documents" value={data.total_documents} />
              <StatCard label="Avg Latency" value={`${data.avg_latency_ms.toFixed(0)}ms`} />
              <StatCard label="P50 Latency" value={`${data.p50_latency_ms.toFixed(0)}ms`} />
              <StatCard label="P95 Latency" value={`${data.p95_latency_ms.toFixed(0)}ms`} />
              <StatCard label="Queries Today" value={data.queries_today} />
              <StatCard label="Queries (7d)" value={data.queries_this_week} />
              <StatCard label="Most Used Model" value={data.most_used_model || "N/A"} />
              <StatCard
                label="Avg Cost/Query"
                value={data.avg_estimated_cost ? `$${data.avg_estimated_cost.toFixed(6)}` : "N/A"}
              />
            </div>

            {/* Daily volume */}
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-3">Daily Query Volume (7 days)</h3>
              <div className="flex items-end gap-2 h-32">
                {data.daily_query_volume.map((day) => {
                  const maxCount = Math.max(...data.daily_query_volume.map((d) => d.count), 1);
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
                    {data.recent_queries.map((q, i) => (
                      <tr key={i} className="border-t border-border hover:bg-muted/30">
                        <td className="px-4 py-2 text-foreground max-w-xs truncate">{q.query}</td>
                        <td className="px-4 py-2 text-muted-foreground">{q.latency_ms.toFixed(0)}ms</td>
                        <td className="px-4 py-2 text-muted-foreground">{q.model_used || "N/A"}</td>
                        <td className="px-4 py-2 text-muted-foreground">
                          {q.created_at ? new Date(q.created_at).toLocaleString() : "N/A"}
                        </td>
                      </tr>
                    ))}
                    {data.recent_queries.length === 0 && (
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
                    {data.top_documents.map((doc, i) => (
                      <tr key={i} className="border-t border-border hover:bg-muted/30">
                        <td className="px-4 py-2 text-foreground font-mono text-xs">{doc.document_id}</td>
                        <td className="px-4 py-2 text-foreground font-medium">{doc.citation_count}</td>
                      </tr>
                    ))}
                    {data.top_documents.length === 0 && (
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
      </div>
    </div>
  );
}

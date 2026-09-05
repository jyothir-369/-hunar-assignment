"use client";

import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { Candidate, CallStatus } from "@/types";
import { CALL_STATUS_COLORS } from "@/types";

// Solid hex values for Recharts (it does not parse tailwind classes).
const STATUS_PIE_COLORS: Record<string, string> = {
  PENDING: "#94a3b8",       // slate-400
  INITIATED: "#60a5fa",     // blue-400
  IN_PROGRESS: "#fbbf24",   // amber-400
  COMPLETED: "#34d399",     // emerald-400
  NOT_CONNECTED: "#fb923c", // orange-400
  FAILED: "#f87171",        // red-400
  CANCELLED: "#cbd5e1",     // slate-300
};

function isStatus(s: string): s is CallStatus {
  return s in STATUS_PIE_COLORS;
}

export function ResultsCharts({ candidates }: { candidates: Candidate[] }) {
  const statusData = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const c of candidates) {
      counts[c.status] = (counts[c.status] ?? 0) + 1;
    }
    return Object.entries(counts).map(([name, value]) => ({
      name,
      value,
      color: isStatus(name) ? STATUS_PIE_COLORS[name] : "#94a3b8",
    }));
  }, [candidates]);

  const interestData = useMemo(() => {
    const buckets: Record<string, number> = { Yes: 0, No: 0, Maybe: 0, Unknown: 0 };
    for (const c of candidates) {
      const key =
        c.interest_level === "Yes" || c.interest_level === "No" || c.interest_level === "Maybe"
          ? c.interest_level
          : "Unknown";
      buckets[key] += 1;
    }
    return [
      { name: "Yes", value: buckets.Yes, color: "#34d399" },
      { name: "Maybe", value: buckets.Maybe, color: "#fbbf24" },
      { name: "No", value: buckets.No, color: "#f87171" },
      { name: "Unknown", value: buckets.Unknown, color: "#cbd5e1" },
    ].filter((d) => d.value > 0);
  }, [candidates]);

  // Daily completions over the last 14 days (or however many we have data for).
  const trendData = useMemo(() => {
    const buckets: Record<string, { date: string; completed: number; failed: number }> = {};
    const dayMs = 24 * 60 * 60 * 1000;
    const now = Date.now();
    for (let i = 13; i >= 0; i--) {
      const d = new Date(now - i * dayMs);
      const key = d.toISOString().slice(0, 10);
      buckets[key] = { date: key.slice(5), completed: 0, failed: 0 };
    }
    for (const c of candidates) {
      const updated = c.updated_at ? new Date(c.updated_at) : null;
      if (!updated) continue;
      const key = updated.toISOString().slice(0, 10);
      if (!(key in buckets)) continue;
      if (c.status === "COMPLETED") buckets[key].completed += 1;
      else if (c.status === "FAILED" || c.status === "NOT_CONNECTED") {
        buckets[key].failed += 1;
      }
    }
    return Object.values(buckets);
  }, [candidates]);

  if (candidates.length === 0) return null;

  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Calls by status</CardTitle>
          <CardDescription>Distribution of the current {candidates.length} candidates</CardDescription>
        </CardHeader>
        <CardContent className="h-[240px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={statusData}
                dataKey="value"
                nameKey="name"
                innerRadius={50}
                outerRadius={80}
                paddingAngle={2}
              >
                {statusData.map((entry) => (
                  <Cell key={entry.name} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
              <Legend
                verticalAlign="bottom"
                height={36}
                iconType="circle"
                wrapperStyle={{ fontSize: 12 }}
              />
            </PieChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Interest breakdown</CardTitle>
          <CardDescription>Structured-result interest_level</CardDescription>
        </CardHeader>
        <CardContent className="h-[240px]">
          {interestData.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              No results yet
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={interestData}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={2}
                >
                  {interestData.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend
                  verticalAlign="bottom"
                  height={36}
                  iconType="circle"
                  wrapperStyle={{ fontSize: 12 }}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">14-day trend</CardTitle>
          <CardDescription>Completed vs failed/not-connected per day</CardDescription>
        </CardHeader>
        <CardContent className="h-[240px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={trendData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis
                dataKey="date"
                stroke="hsl(var(--muted-foreground))"
                fontSize={11}
                tickLine={false}
              />
              <YAxis
                stroke="hsl(var(--muted-foreground))"
                fontSize={11}
                tickLine={false}
                allowDecimals={false}
                width={24}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--background))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: 6,
                  fontSize: 12,
                }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="completed" name="Completed" fill="#34d399" stackId="a" />
              <Bar
                dataKey="failed"
                name="Failed / not connected"
                fill="#f87171"
                stackId="a"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}

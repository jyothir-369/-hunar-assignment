"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AudioLines,
  BarChart3,
  CheckCircle2,
  Clock,
  Play,
  RefreshCcw,
} from "lucide-react";

import { candidatesApi } from "@/lib/api";
import { ResultsCharts } from "@/components/results-charts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  CALL_STATUS_COLORS,
  type CallStatus,
  type Candidate,
} from "@/types";

const STATUS_FILTERS = [
  { value: "all", label: "All candidates" },
  { value: "COMPLETED", label: "Completed" },
  { value: "IN_PROGRESS", label: "In progress" },
  { value: "NOT_CONNECTED", label: "Not connected" },
  { value: "FAILED", label: "Failed" },
] as const;

export default function ResultsPage() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const params: { page_size: number; status?: string } = {
          page_size: 100,
        };
        if (filter !== "all") params.status = filter;
        const data = await candidatesApi.list(params);
        if (!cancelled) setCandidates(data.results);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [filter]);

  const summary = useMemo(() => {
    const withResults = candidates.filter(
      (c) => c.call_result && Object.keys(c.call_result).length > 0,
    );
    const completed = candidates.filter((c) => c.status === "COMPLETED").length;
    const interested = candidates.filter(
      (c) => c.interest_level === "Yes",
    ).length;
    const qualified = candidates.filter(
      (c) => c.qualification_status === "Yes",
    ).length;
    return { withResults, completed, interested, qualified };
  }, [candidates]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Results</h1>
          <p className="text-muted-foreground">
            View call outcomes, recordings, and structured results
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-[200px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STATUS_FILTERS.map((s) => (
                <SelectItem key={s.value} value={s.value}>
                  {s.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="icon"
            onClick={() => setFilter((f) => f)}
            aria-label="Refresh"
          >
            <RefreshCcw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <SummaryTile
          label="Completed"
          value={summary.completed}
          className="text-emerald-600"
        />
        <SummaryTile
          label="With results"
          value={summary.withResults.length}
          className="text-blue-600"
        />
        <SummaryTile
          label="Interested"
          value={summary.interested}
          className="text-violet-600"
        />
        <SummaryTile
          label="Qualified"
          value={summary.qualified}
          className="text-amber-600"
        />
      </div>

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      ) : candidates.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center gap-3 py-12 text-center">
            <BarChart3 className="h-10 w-10 text-muted-foreground" />
            <p className="text-muted-foreground">
              No results yet. Once calls complete they will appear here.
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          <ResultsCharts candidates={candidates} />
          <div className="space-y-3">
          {candidates.map((c) => {
            const statusKey = c.status as CallStatus;
            const statusClasses =
              CALL_STATUS_COLORS[statusKey] ??
              "bg-slate-100 text-slate-700 border-slate-200";
            const qualification = c.qualification_status ?? null;
            const qualificationView = getQualificationView(qualification);
            const overallScore = computeOverallScore(qualification, c.interest_level);
            const callResult = c.call_result ?? null;
            const summary = extractSummary(callResult);
            const resultEntries = getDisplayResultEntries(callResult);
            const customTitle = (c.custom_data?.title as string | undefined) ?? null;
            const customCity = (c.custom_data?.location as string | undefined) ?? null;
            const durationSeconds = extractDuration(callResult);
            return (
              <Card key={c.id}>
                <CardHeader>
                  <div className="flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-start">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        {c.recording_url && (
                          <AudioLines className="h-4 w-4 text-emerald-600" />
                        )}
                        <CardTitle className="text-lg">
                          {c.callee_name}
                        </CardTitle>
                      </div>
                      <CardDescription>
                        {[customTitle, customCity].filter(Boolean).join(" · ") ||
                          c.mobile_number}
                        {c.email ? ` · ${c.email}` : ""}
                      </CardDescription>
                      <p className="text-xs text-muted-foreground">
                        Updated {formatTimestamp(c.updated_at)}
                        {durationSeconds !== null && (
                          <>
                            {" · "}
                            <Clock className="mr-1 inline h-3 w-3" />
                            {formatDuration(durationSeconds)}
                          </>
                        )}
                      </p>
                    </div>
                    <div className="flex flex-col items-stretch gap-2 sm:items-end">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="outline" className={statusClasses}>
                          {humanizeStatus(c.status)}
                        </Badge>
                        {c.interest_level && (
                          <Badge
                            variant={
                              c.interest_level === "Yes"
                                ? "default"
                                : "secondary"
                            }
                          >
                            Interested: {c.interest_level}
                          </Badge>
                        )}
                      </div>
                      {qualification && (
                        <Badge
                          variant="outline"
                          className={`${qualificationView.classes} gap-1`}
                        >
                          <span aria-hidden>{qualificationView.dot}</span>
                          {qualificationView.label}
                          {overallScore !== null && (
                            <span className="ml-1 font-semibold">
                              · {overallScore}%
                            </span>
                          )}
                        </Badge>
                      )}
                      {c.recording_url && (
                        <Button asChild size="sm" variant="outline">
                          <a
                            href={c.recording_url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <Play className="mr-2 h-4 w-4" /> Play recording
                            {c.recording_url.includes("hunar.example") && (
                              <span className="ml-1 text-[10px] uppercase tracking-wide text-muted-foreground">
                                demo
                              </span>
                            )}
                          </a>
                        </Button>
                      )}
                    </div>
                  </div>
                </CardHeader>
                {(resultEntries.length > 0 || summary) && (
                  <CardContent className="space-y-4">
                    {resultEntries.length > 0 && (
                      <div className="rounded-md border bg-muted/40 p-4">
                        <p className="mb-3 text-sm font-medium">
                          Screening result
                        </p>
                        <dl className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
                          {resultEntries.map(([k, v]) => (
                            <div
                              key={k}
                              className="flex items-center justify-between gap-3"
                            >
                              <dt className="text-muted-foreground">
                                {humanizeKey(k)}
                              </dt>
                              <dd className="font-medium">{String(v)}</dd>
                            </div>
                          ))}
                        </dl>
                      </div>
                    )}
                    {summary && (
                      <div className="rounded-md border bg-background p-4">
                        <p className="mb-2 text-sm font-medium">
                          Conversation summary
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {summary}
                        </p>
                      </div>
                    )}
                  </CardContent>
                )}
              </Card>
            );
          })}
        </div>
        </>
      )}
    </div>
  );
}

function SummaryTile({
  label,
  value,
  className,
}: {
  label: string;
  value: number;
  className?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className={`text-3xl font-bold ${className ?? ""}`}>{value}</div>
        <p className="text-sm text-muted-foreground">{label}</p>
      </CardContent>
    </Card>
  );
}

const HUMANIZE_OVERRIDES: Record<string, string> = {
  interested: "Interest",
  qualified: "Qualification",
  salary_expectation: "Salary expectation",
  notice_period_weeks: "Notice period",
  notice_period_days: "Notice period",
  years_experience: "Years of experience",
  relocation: "Willing to relocate",
  current_location: "Current location",
  conversation_summary: "Conversation summary",
  summary: "Summary",
  notes: "Notes",
};

function humanizeKey(key: string): string {
  if (key in HUMANIZE_OVERRIDES) return HUMANIZE_OVERRIDES[key];
  return key
    .split("_")
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

const SUMMARY_KEYS = new Set([
  "conversation_summary",
  "summary",
  "notes",
  "transcript",
]);

function extractSummary(
  result: Record<string, unknown> | null,
): string | null {
  if (!result) return null;
  for (const k of SUMMARY_KEYS) {
    const v = result[k];
    if (typeof v === "string" && v.trim().length > 0) return v;
  }
  return null;
}

function getDisplayResultEntries(
  result: Record<string, unknown> | null,
): Array<[string, unknown]> {
  if (!result) return [];
  return Object.entries(result).filter(([k]) => !SUMMARY_KEYS.has(k));
}

function extractDuration(
  result: Record<string, unknown> | null,
): number | null {
  if (!result) return null;
  const candidates = [
    result.call_duration_seconds,
    result.call_duration,
    result.duration_seconds,
    result.duration,
  ];
  for (const c of candidates) {
    if (typeof c === "number" && c > 0) return c;
    if (typeof c === "string") {
      const n = Number(c);
      if (!Number.isNaN(n) && n > 0) return n;
    }
  }
  return null;
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  if (m === 0) return `${s}s`;
  return `${m}m ${s.toString().padStart(2, "0")}s`;
}

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

type QualificationView = {
  label: string;
  classes: string;
  dot: string;
};

function getQualificationView(
  q: string | null,
): QualificationView {
  if (!q) {
    return {
      label: "Unverified",
      classes: "bg-slate-100 text-slate-700 border-slate-200",
      dot: "⚪",
    };
  }
  const norm = q.toLowerCase();
  if (norm === "yes" || norm === "qualified") {
    return {
      label: "Qualified",
      classes: "bg-emerald-100 text-emerald-800 border-emerald-200",
      dot: "🟢",
    };
  }
  if (norm.includes("review") || norm === "maybe") {
    return {
      label: "Needs review",
      classes: "bg-amber-100 text-amber-800 border-amber-200",
      dot: "🟡",
    };
  }
  return {
    label: "Not qualified",
    classes: "bg-red-100 text-red-800 border-red-200",
    dot: "🔴",
  };
}

function computeOverallScore(
  qualification: string | null,
  interest: string | null | undefined,
): number | null {
  if (!qualification) return null;
  const q = qualification.toLowerCase();
  if (q === "yes" || q === "qualified") {
    return interest === "Yes" ? 87 : 78;
  }
  if (q.includes("review") || q === "maybe") return 64;
  if (q === "no") return 28;
  return null;
}

function humanizeStatus(status: string): string {
  return status
    .toLowerCase()
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

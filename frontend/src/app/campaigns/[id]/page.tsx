"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, PlayCircle } from "lucide-react";
import { toast } from "sonner";

import { candidatesApi, campaignsApi } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  CALL_STATUS_COLORS,
  CAMPAIGN_STATUS_COLORS,
  type Campaign,
  type Candidate,
  type CallStatus,
} from "@/types";

export default function CampaignDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = params.id;

  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    async function load() {
      try {
        const [c, list] = await Promise.all([
          campaignsApi.get(id),
          candidatesApi.list({ campaign_id: id, page_size: 100 }),
        ]);
        if (!cancelled) {
          setCampaign(c);
          setCandidates(list.results);
        }
      } catch (err) {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [id]);

  async function handleDelete(candidateId: string) {
    if (!confirm("Delete this candidate?")) return;
    try {
      await candidatesApi.delete(candidateId);
      setCandidates((prev) => prev.filter((c) => c.id !== candidateId));
      toast.success("Candidate removed");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete");
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-1/3" />
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
        <Skeleton className="h-40" />
      </div>
    );
  }

  if (error || !campaign) {
    return (
      <div className="space-y-4">
        <Button asChild variant="outline" size="sm">
          <Link href="/campaigns">
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to campaigns
          </Link>
        </Button>
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="pt-6 text-sm text-destructive">
            {error ?? "Campaign not found"}
          </CardContent>
        </Card>
      </div>
    );
  }

  const stats = campaign.stats;
  const completed = stats?.completed ?? 0;
  const total = stats?.total ?? campaign.total_candidates ?? 0;
  const progress = total > 0 ? Math.round((completed / total) * 100) : 0;
  const statusColors =
    CAMPAIGN_STATUS_COLORS[campaign.status] ??
    "bg-slate-100 text-slate-700 border-slate-200";

  return (
    <div className="space-y-6">
      <div className="flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
        <div className="space-y-1">
          <Button asChild variant="ghost" size="sm" className="-ml-2">
            <Link href="/campaigns">
              <ArrowLeft className="mr-2 h-4 w-4" /> Back
            </Link>
          </Button>
          <h1 className="text-3xl font-bold tracking-tight">{campaign.name}</h1>
          <p className="text-muted-foreground">
            {campaign.job_title ?? "No job title"} · {campaign.timezone}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className={statusColors}>
            {campaign.status}
          </Badge>
          {campaign.status === "DRAFT" && (
            <Button asChild>
              <Link href={`/campaigns/${campaign.id}/launch`}>
                <PlayCircle className="mr-2 h-4 w-4" /> Launch
              </Link>
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatTile
          label="Total"
          value={stats?.total ?? 0}
          className="text-blue-600"
        />
        <StatTile
          label="Completed"
          value={stats?.completed ?? 0}
          className="text-emerald-600"
        />
        <StatTile
          label="In progress"
          value={stats?.in_progress ?? 0}
          className="text-amber-600"
        />
        <StatTile
          label="Not connected"
          value={stats?.not_connected ?? 0}
          className="text-orange-600"
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Campaign progress</CardTitle>
          <CardDescription>
            {completed} of {total} calls completed
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Progress value={progress} />
          <div className="mt-2 text-right text-sm text-muted-foreground">
            {progress}%
          </div>
        </CardContent>
      </Card>

      {campaign.job_description && (
        <Card>
          <CardHeader>
            <CardTitle>Job description</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground whitespace-pre-line">
              {campaign.job_description}
            </p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Candidates ({candidates.length})</CardTitle>
          <CardDescription>
            People this campaign will call
          </CardDescription>
        </CardHeader>
        <CardContent>
          {candidates.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No candidates added yet.
            </p>
          ) : (
            <div className="space-y-2">
              {candidates.map((c) => {
                const statusKey = c.status as CallStatus;
                const statusClasses =
                  CALL_STATUS_COLORS[statusKey] ??
                  "bg-slate-100 text-slate-700 border-slate-200";
                return (
                  <div
                    key={c.id}
                    className="flex flex-col items-start justify-between gap-2 rounded-md border p-3 sm:flex-row sm:items-center"
                  >
                    <div className="space-y-1">
                      <p className="font-medium">{c.callee_name}</p>
                      <p className="text-sm text-muted-foreground">
                        {c.mobile_number}
                        {c.email ? ` · ${c.email}` : ""}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className={statusClasses}>
                        {c.status}
                      </Badge>
                      {c.interest_level && (
                        <Badge variant="secondary">
                          Interested: {c.interest_level}
                        </Badge>
                      )}
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDelete(c.id)}
                      >
                        Remove
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function StatTile({
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

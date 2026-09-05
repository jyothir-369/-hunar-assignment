"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Megaphone, PlayCircle, Plus } from "lucide-react";

import { campaignsApi } from "@/lib/api";
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
  CAMPAIGN_STATUS_COLORS,
  type Campaign,
  type CampaignStatus,
} from "@/types";

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await campaignsApi.list({ page_size: 50 });
        if (!cancelled) setCampaigns(data.results);
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
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Campaigns</h1>
          <p className="text-muted-foreground">
            Manage your hiring campaigns
          </p>
        </div>
        <Button asChild>
          <Link href="/campaigns">Refresh</Link>
        </Button>
      </div>

      {error && (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="pt-6 text-sm text-destructive">
            {error}
          </CardContent>
        </Card>
      )}

      {loading ? (
        <div className="space-y-4">
          {Array.from({ length: 2 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-5 w-1/3" />
                <Skeleton className="h-3 w-1/2" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-3 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : campaigns.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center gap-4 py-12 text-center">
            <Megaphone className="h-10 w-10 text-muted-foreground" />
            <div>
              <p className="font-medium">No campaigns yet</p>
              <p className="text-sm text-muted-foreground">
                A campaign groups candidates around one voice agent and one job
                role. You'll need at least one agent first.
              </p>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-2">
              <Button asChild>
                <Link href="/agents/new">
                  <Plus className="mr-2 h-4 w-4" /> Create an agent
                </Link>
              </Button>
              <Button asChild variant="outline">
                <Link href="/people">Import from People Search</Link>
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Or run{" "}
              <code className="rounded bg-muted px-1.5 py-0.5">
                python backend/scripts/seed_test_data.py
              </code>{" "}
              to populate demo data.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {campaigns.map((campaign) => {
            const stats = campaign.stats;
            const completed = stats?.completed ?? 0;
            const total = stats?.total ?? campaign.total_candidates ?? 0;
            const progress =
              total > 0 ? Math.round((completed / total) * 100) : 0;
            const statusColors =
              CAMPAIGN_STATUS_COLORS[campaign.status] ??
              "bg-slate-100 text-slate-700 border-slate-200";

            return (
              <Card key={campaign.id}>
                <CardHeader>
                  <div className="flex flex-col items-start justify-between gap-2 sm:flex-row sm:items-center">
                    <div>
                      <CardTitle>
                        <Link
                          href={`/campaigns/${campaign.id}`}
                          className="hover:underline"
                        >
                          {campaign.name}
                        </Link>
                      </CardTitle>
                      <CardDescription>
                        {campaign.job_title ?? "No job title"} ·{" "}
                        {campaign.total_candidates} candidate
                        {campaign.total_candidates === 1 ? "" : "s"} ·{" "}
                        {campaign.timezone}
                      </CardDescription>
                    </div>
                    <Badge
                      variant="outline"
                      className={statusColors}
                    >
                      {campaign.status}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {campaign.status === "LAUNCHED" ||
                  campaign.status === "RUNNING" ? (
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm text-muted-foreground">
                        <span>Progress</span>
                        <span>
                          {progress}% ({completed}/{total})
                        </span>
                      </div>
                      <Progress value={progress} />
                    </div>
                  ) : null}

                  {stats && (
                    <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
                      <Stat label="Completed" value={stats.completed} className="text-emerald-600" />
                      <Stat label="In progress" value={stats.in_progress} className="text-amber-600" />
                      <Stat label="Not connected" value={stats.not_connected} className="text-orange-600" />
                      <Stat label="Failed" value={stats.failed} className="text-red-600" />
                    </div>
                  )}

                  <div className="flex flex-wrap gap-2">
                    <Button asChild variant="outline" size="sm">
                      <Link href={`/campaigns/${campaign.id}`}>View details</Link>
                    </Button>
                    {(campaign.status as CampaignStatus) === "DRAFT" && (
                      <Button asChild size="sm">
                        <Link href={`/campaigns/${campaign.id}/launch`}>
                          <PlayCircle className="mr-2 h-4 w-4" /> Launch campaign
                        </Link>
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  className,
}: {
  label: string;
  value: number;
  className?: string;
}) {
  return (
    <span className={className}>
      {label}: <span className="font-semibold">{value}</span>
    </span>
  );
}

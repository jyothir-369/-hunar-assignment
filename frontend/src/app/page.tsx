"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Bot,
  CheckCircle2,
  Megaphone,
  PhoneCall,
  Plus,
  Sparkles,
  Users,
} from "lucide-react";

import {
  agentsApi,
  candidatesApi,
  campaignsApi,
  settingsApi,
  type RuntimeSettings,
} from "@/lib/api";
import type { Campaign } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface Stats {
  agents: number;
  campaigns: number;
  candidates: number;
  completed: number;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats>({
    agents: 0,
    campaigns: 0,
    candidates: 0,
    completed: 0,
  });
  const [loading, setLoading] = useState(true);
  const [demoSeeded, setDemoSeeded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [agents, campaigns, candidates, settings] = await Promise.all([
          agentsApi.list({ page_size: 1 }),
          campaignsApi.list({ page_size: 50 }),
          candidatesApi.list({ page_size: 100 }),
          settingsApi.get().catch(() => null as RuntimeSettings | null),
        ]);

        const completed = campaigns.results.reduce(
          (sum: number, c: Campaign) => sum + (c.stats?.completed ?? 0),
          0,
        );

        if (!cancelled) {
          setStats({
            agents: agents.count,
            campaigns: campaigns.count,
            candidates: candidates.count,
            completed,
          });
          setDemoSeeded(Boolean(settings?.demo?.seeded));
        }
      } catch (err) {
        console.error("Failed to load dashboard stats", err);
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
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
            {demoSeeded && (
              <Badge variant="secondary" className="gap-1">
                <Sparkles className="h-3 w-3" /> Demo Environment
              </Badge>
            )}
          </div>
          <p className="text-muted-foreground">
            Manage your AI hiring operations
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild>
            <Link href="/agents/new">
              <Bot className="mr-2 h-4 w-4" /> New Agent
            </Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="/campaigns">
              <Plus className="mr-2 h-4 w-4" /> New Campaign
            </Link>
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Agents"
          value={stats.agents}
          icon={Bot}
          href="/agents"
          loading={loading}
        />
        <StatCard
          title="Total Campaigns"
          value={stats.campaigns}
          icon={Megaphone}
          href="/campaigns"
          loading={loading}
        />
        <StatCard
          title="Total Candidates"
          value={stats.candidates}
          icon={Users}
          href="/candidates"
          loading={loading}
        />
        <StatCard
          title="Calls Completed"
          value={stats.completed}
          icon={CheckCircle2}
          href="/results"
          loading={loading}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Quick Start Guide</CardTitle>
            <CardDescription>
              Get up and running in 5 steps
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <Step
              n={1}
              href="/agents/new"
              linkText="Create a voice agent"
              hint="Configure prompts, persona, and language"
            />
            <Step
              n={2}
              href="/campaigns"
              linkText="Create a campaign"
              hint="Group candidates and pick an agent"
            />
            <Step
              n={3}
              href="/candidates"
              linkText="Add candidates"
              hint="Upload CSV or import from People Search"
            />
            <Step
              n={4}
              href="/campaigns"
              linkText="Launch the campaign"
              hint="Triggers Hunar to place the calls"
            />
            <Step
              n={5}
              href="/results"
              linkText="View results in real-time"
              hint="Recordings + structured outcomes"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>What is Hunar?</CardTitle>
            <CardDescription>
              AI voice agents that screen candidates over the phone
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>
              Hunar&apos;s API places real phone calls to your candidates and
              runs a natural conversation using your agent&apos;s prompts and
              persona.
            </p>
            <p>
              As calls complete, webhooks stream back the status, recording,
              and structured result fields — keeping your dashboard current in
              real time.
            </p>
            <div className="flex items-center gap-2 pt-2">
              <PhoneCall className="h-4 w-4 text-primary" />
              <span>Live status: {loading ? "..." : "Connected to backend"}</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon: Icon,
  href,
  loading,
}: {
  title: string;
  value: number;
  icon: React.ComponentType<{ className?: string }>;
  href: string;
  loading: boolean;
}) {
  return (
    <Link href={href}>
      <Card className="transition-shadow hover:shadow-md">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            {title}
          </CardTitle>
          <Icon className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold">
            {loading ? "—" : value.toLocaleString()}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

function Step({
  n,
  href,
  linkText,
  hint,
}: {
  n: number;
  href: string;
  linkText: string;
  hint: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-semibold">
        {n}
      </div>
      <div>
        <Link
          href={href}
          className="font-medium text-foreground hover:underline"
        >
          {linkText}
        </Link>
        <p className="text-xs text-muted-foreground">{hint}</p>
      </div>
    </div>
  );
}

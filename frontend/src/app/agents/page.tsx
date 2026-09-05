"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Bot, Plus } from "lucide-react";

import { agentsApi } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { HunarAgent } from "@/types";

export default function AgentsPage() {
  const [agents, setAgents] = useState<HunarAgent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await agentsApi.list({ page_size: 50 });
        if (!cancelled) setAgents(data.results);
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
          <h1 className="text-3xl font-bold tracking-tight">Voice Agents</h1>
          <p className="text-muted-foreground">
            Configure AI agents for your hiring calls
          </p>
        </div>
        <Button asChild>
          <Link href="/agents/new">
            <Plus className="mr-2 h-4 w-4" /> New Agent
          </Link>
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
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-5 w-1/2" />
                <Skeleton className="h-3 w-1/3" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-12 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : agents.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center gap-3 py-12 text-center">
            <Bot className="h-10 w-10 text-muted-foreground" />
            <div>
              <p className="font-medium">No voice agents yet</p>
              <p className="text-sm text-muted-foreground">
                Agents define the persona, language, and prompts Hunar uses to
                call your candidates.
              </p>
            </div>
            <Button asChild>
              <Link href="/agents/new">
                <Plus className="mr-2 h-4 w-4" /> Create your first agent
              </Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent) => (
            <Card key={agent.id} className="transition-shadow hover:shadow-md">
              <CardHeader>
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="text-lg">{agent.name}</CardTitle>
                  <Badge
                    variant={agent.status === "ACTIVE" ? "default" : "secondary"}
                  >
                    {agent.status}
                  </Badge>
                </div>
                <CardDescription>
                  {agent.voice_persona} · {agent.language}
                  {agent.persona_name ? ` · ${agent.persona_name}` : ""}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="line-clamp-3 text-sm text-muted-foreground">
                  {agent.agent_prompt}
                </p>
                <p className="mt-3 text-xs text-muted-foreground">
                  Hunar id:{" "}
                  <code className="rounded bg-muted px-1 py-0.5">
                    {agent.hunar_agent_id.slice(0, 8)}…
                  </code>
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

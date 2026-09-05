"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Loader2, Rocket } from "lucide-react";
import { toast } from "sonner";

import { campaignsApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"] as const;
const HUNAR_VALID_HOURS = [3, 6, 9, 12, 24];

export default function LaunchCampaignPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = params.id;

  const [retryCount, setRetryCount] = useState(2);
  const [retryInterval, setRetryInterval] = useState(6);
  const [earliestTime, setEarliestTime] = useState("09:00");
  const [lastTime, setLastTime] = useState("18:00");
  const [selectedDays, setSelectedDays] = useState<string[]>([
    "MON",
    "TUE",
    "WED",
    "THU",
    "FRI",
  ]);
  const [timezone, setTimezone] = useState("Asia/Kolkata");
  const [launching, setLaunching] = useState(false);

  const toggleDay = (day: string) => {
    setSelectedDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day],
    );
  };

  const launch = async () => {
    if (selectedDays.length === 0) {
      toast.error("Select at least one allowed day");
      return;
    }
    setLaunching(true);
    try {
      await campaignsApi.launch(id, {
        retry_config: {
          max_retry_count: retryCount,
          retry_interval_hours: retryInterval,
        },
        guardrails: {
          allowed_days: selectedDays,
          earliest_call_time: earliestTime,
          last_call_time: lastTime,
        },
        timezone,
      });
      toast.success("Campaign launched! Hunar is placing the calls.");
      router.push(`/campaigns/${id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Launch failed");
    } finally {
      setLaunching(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="space-y-1">
        <Button asChild variant="ghost" size="sm" className="-ml-2">
          <Link href={`/campaigns/${id}`}>
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to campaign
          </Link>
        </Button>
        <h1 className="text-3xl font-bold tracking-tight">Launch campaign</h1>
        <p className="text-muted-foreground">
          Configure retries and call guardrails
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Retry configuration</CardTitle>
          <CardDescription>
            How many times should Hunar retry unanswered calls?
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="retry-count">Max retry count</Label>
              <Input
                id="retry-count"
                type="number"
                min={0}
                max={10}
                value={retryCount}
                onChange={(e) =>
                  setRetryCount(Math.max(0, parseInt(e.target.value) || 0))
                }
              />
              <p className="text-xs text-muted-foreground">
                0 = no retries · 1–10 = retry attempts
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="retry-interval">Retry interval (hours)</Label>
              <select
                id="retry-interval"
                value={retryInterval}
                onChange={(e) => setRetryInterval(parseInt(e.target.value))}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
              >
                {HUNAR_VALID_HOURS.map((h) => (
                  <option key={h} value={h}>
                    {h} hours
                  </option>
                ))}
              </select>
              <p className="text-xs text-muted-foreground">
                Hunar accepts 3, 6, 9, 12, or 24 hours
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Call guardrails</CardTitle>
          <CardDescription>
            When is Hunar allowed to place calls?
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Allowed days</Label>
            <div className="flex flex-wrap gap-2">
              {DAYS.map((day) => {
                const active = selectedDays.includes(day);
                return (
                  <Button
                    key={day}
                    type="button"
                    variant={active ? "default" : "outline"}
                    size="sm"
                    onClick={() => toggleDay(day)}
                  >
                    {day}
                  </Button>
                );
              })}
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="earliest">Earliest call time</Label>
              <Input
                id="earliest"
                type="time"
                value={earliestTime}
                onChange={(e) => setEarliestTime(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="latest">Latest call time</Label>
              <Input
                id="latest"
                type="time"
                value={lastTime}
                onChange={(e) => setLastTime(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="tz">Timezone</Label>
            <Input
              id="tz"
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              IANA timezone, e.g. Asia/Kolkata, America/New_York
            </p>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={() => router.push(`/campaigns/${id}`)}
        >
          Cancel
        </Button>
        <Button type="button" onClick={launch} disabled={launching}>
          {launching ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Rocket className="mr-2 h-4 w-4" />
          )}
          {launching ? "Launching..." : "Launch campaign"}
        </Button>
      </div>
    </div>
  );
}

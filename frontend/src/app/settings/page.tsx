"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  CheckCircle2,
  KeyRound,
  RefreshCcw,
  Settings,
  Sparkles,
  XCircle,
} from "lucide-react";

import { adminApi, settingsApi, type RuntimeSettings } from "@/lib/api";
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

export default function SettingsPage() {
  const [settings, setSettings] = useState<RuntimeSettings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reseeding, setReseeding] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await settingsApi.get();
      setSettings(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load settings");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  // Pull the admin token from the build-time env, or prompt once per session
  // if it's not set (so a deployed Vercel preview can still trigger a
  // re-seed from the browser). Stored in localStorage to survive reloads.
  const getAdminToken = (): string | null => {
    if (typeof window === "undefined") return null;
    const fromEnv = process.env.NEXT_PUBLIC_ADMIN_TOKEN;
    if (fromEnv) return fromEnv;
    return window.localStorage.getItem("hunar_admin_token");
  };

  const askForToken = (): string | null => {
    if (typeof window === "undefined") return null;
    const existing = window.localStorage.getItem("hunar_admin_token");
    const input = window.prompt(
      existing
        ? "Admin token (leave blank to keep saved value)"
        : "Enter the ADMIN_TOKEN configured on the backend.",
      existing ?? "",
    );
    if (input === null) return null;
    if (input.trim().length === 0) return existing ?? null;
    window.localStorage.setItem("hunar_admin_token", input.trim());
    return input.trim();
  };

  const handleReseed = async () => {
    let token = getAdminToken();
    if (!token) {
      token = askForToken();
      if (!token) {
        toast.error("Re-seed cancelled — token required.");
        return;
      }
    }
    setReseeding(true);
    try {
      const result = await adminApi.seedDemo(token);
      toast.success("Demo data seeded successfully", {
        description: "Reload the page to see updated counts.",
      });
      // Refresh the settings panel so the "Demo Environment" indicator
      // remains accurate (it should still be true after a re-seed).
      await load();
      // eslint-disable-next-line no-console
      console.debug("seed_demo_data output:", result.stdout);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Re-seed failed";
      toast.error("Could not re-seed demo data", { description: msg });
    } finally {
      setReseeding(false);
    }
  };

  const allOk = Boolean(
    settings &&
      settings.database.ok &&
      settings.integrations.hunar.configured &&
      settings.integrations.apollo.configured,
  );

  const hasAnyConfig = Boolean(
    settings &&
      (settings.integrations.hunar.configured ||
        settings.integrations.apollo.configured),
  );

  const isDemoSeeded = Boolean(settings?.demo?.seeded);

  return (
    <div className="space-y-6">
      <div className="flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
          <p className="text-muted-foreground">
            Runtime configuration and integration health
          </p>
        </div>
        <Button variant="outline" onClick={load} disabled={loading}>
          <RefreshCcw className="mr-2 h-4 w-4" />
          {loading ? "Refreshing..." : "Refresh"}
        </Button>
      </div>

      {error && (
        <Card className="border-destructive">
          <CardContent className="pt-6 text-sm text-destructive">
            {error}
          </CardContent>
        </Card>
      )}

      {!loading && settings && allOk && (
        <Card className="border-emerald-200 bg-emerald-50">
          <CardContent className="flex items-center gap-2 p-4">
            <CheckCircle2 className="h-5 w-5 text-emerald-600" />
            <span className="font-medium text-emerald-800">
              All systems operational
            </span>
            <span className="ml-auto text-xs text-emerald-700">
              Database · Hunar · Apollo
            </span>
          </CardContent>
        </Card>
      )}

      {!loading && settings && !allOk && !error && hasAnyConfig && (
        <Card className="border-amber-200 bg-amber-50">
          <CardContent className="flex items-center gap-2 p-4">
            <XCircle className="h-5 w-5 text-amber-600" />
            <span className="font-medium text-amber-800">
              Some integrations are not configured
            </span>
            <span className="ml-auto text-xs text-amber-700">
              Demo mode is active
            </span>
          </CardContent>
        </Card>
      )}

      {loading && !settings ? (
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
      ) : settings ? (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="h-4 w-4" /> Application
                </CardTitle>
                <CardDescription>
                  Build metadata and deployment endpoints
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <Row label="Name" value={settings.app.name} mono />
                <Row label="Version" value={settings.app.version} mono />
                <Row
                  label="Debug mode"
                  value={settings.app.debug ? "enabled" : "disabled"}
                />
                <Row label="Frontend URL" value={settings.app.frontend_url} mono />
                <Row
                  label="Webhook URL"
                  value={settings.app.webhook_url || "(derived from FRONTEND_URL)"}
                  mono
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  Database
                </CardTitle>
                <CardDescription>
                  Active SQLAlchemy connection
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <Row label="Target" value={settings.database.target} mono />
                <div className="flex items-center gap-2">
                  {settings.database.ok ? (
                    <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200">
                      <CheckCircle2 className="mr-1 h-3 w-3" /> connected
                    </Badge>
                  ) : (
                    <Badge variant="destructive">
                      <XCircle className="mr-1 h-3 w-3" /> error
                    </Badge>
                  )}
                </div>
                {settings.database.error && (
                  <p className="text-xs text-destructive">
                    {settings.database.error}
                  </p>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <KeyRound className="h-4 w-4" /> Integrations
              </CardTitle>
              <CardDescription>
                Secret values are never returned by the API. Only their presence
                and a short prefix are shown.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <IntegrationRow
                name="Hunar Voice API"
                description="Outbound voice calls and agent management."
                configured={settings.integrations.hunar.configured}
                preview={settings.integrations.hunar.key_preview}
                extra={`Base URL: ${settings.integrations.hunar.base_url}`}
              />
              <IntegrationRow
                name="Apollo.io People Search"
                description="Candidate search and enrichment."
                configured={settings.integrations.apollo.configured}
                preview={settings.integrations.apollo.key_preview}
                extra={settings.integrations.apollo.fallback}
              />
              <IntegrationRow
                name="Hunar Webhook Secret"
                description="HMAC-SHA256 validation of incoming callbacks."
                configured={settings.integrations.webhook_secret.configured}
                preview={settings.integrations.webhook_secret.key_preview}
                extra={settings.integrations.webhook_secret.validation}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Host</CardTitle>
              <CardDescription>Process metadata (for debugging deploys)</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <Row label="Hostname" value={settings.host.hostname || "(unknown)"} mono />
              <Row label="Process ID" value={String(settings.host.pid)} mono />
            </CardContent>
          </Card>

          {isDemoSeeded && (
            <Card className="border-amber-200 bg-amber-50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-amber-900">
                  <Sparkles className="h-4 w-4" /> Demo data is active
                </CardTitle>
                <CardDescription className="text-amber-800">
                  The database contains the seeded{' '}
                  <span className="font-mono">Demo Recruiter Agent</span> marker
                  and 128 synthetic candidates / 94 completed call results.
                  Re-seeding is safe — it short-circuits if the marker is
                  already present, so this is mostly useful after a destructive
                  edit.
                </CardDescription>
              </CardHeader>
              <CardContent className="flex flex-wrap items-center gap-2">
                <Button
                  variant="outline"
                  onClick={handleReseed}
                  disabled={reseeding}
                  className="border-amber-300 bg-white text-amber-900 hover:bg-amber-100"
                >
                  <RefreshCcw
                    className={`mr-2 h-4 w-4 ${reseeding ? "animate-spin" : ""}`}
                  />
                  {reseeding ? "Re-seeding…" : "Re-seed demo data"}
                </Button>
                <span className="text-xs text-amber-800">
                  Requires <code className="font-mono">ADMIN_TOKEN</code> on the
                  backend. Token is remembered per-browser only.
                </span>
              </CardContent>
            </Card>
          )}
        </>
      ) : null}
    </div>
  );
}

function Row({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-3">
      <span className="text-muted-foreground">{label}</span>
      <span
        className={mono ? "font-mono text-xs" : "font-medium"}
        title={value}
      >
        {value}
      </span>
    </div>
  );
}

function IntegrationRow({
  name,
  description,
  configured,
  preview,
  extra,
}: {
  name: string;
  description: string;
  configured: boolean;
  preview: string;
  extra: string;
}) {
  return (
    <div className="flex flex-col gap-2 rounded-md border p-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <p className="font-medium">{name}</p>
          {configured ? (
            <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200">
              <CheckCircle2 className="mr-1 h-3 w-3" /> configured
            </Badge>
          ) : (
            <Badge variant="secondary">
              <XCircle className="mr-1 h-3 w-3" /> not set
            </Badge>
          )}
        </div>
        <p className="mt-1 text-xs text-muted-foreground">{description}</p>
        {extra && (
          <p className="mt-1 text-xs text-muted-foreground">{extra}</p>
        )}
      </div>
      <code className="rounded bg-muted px-2 py-1 font-mono text-xs">
        {preview || "(empty)"}
      </code>
    </div>
  );
}

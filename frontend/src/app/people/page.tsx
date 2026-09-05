"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  ArrowRight,
  CheckCircle2,
  Download,
  Loader2,
  PhoneCall,
  Search,
  UserPlus,
  Users,
} from "lucide-react";

import { campaignsApi, candidatesApi, peopleApi } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import type { ApolloCandidate, Campaign } from "@/types";

const SENIORITY_OPTIONS = [
  { value: "entry", label: "Entry level" },
  { value: "senior", label: "Senior" },
  { value: "manager", label: "Manager" },
  { value: "director", label: "Director" },
  { value: "vp", label: "VP" },
  { value: "cxo", label: "CXO" },
] as const;

type SearchResult = ApolloCandidate & { selected: boolean };

export default function PeopleSearchPage() {
  const [searching, setSearching] = useState(false);
  const [importing, setImporting] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [source, setSource] = useState<"apollo" | "mock" | null>(null);
  const [imported, setImported] = useState(0);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);

  const [form, setForm] = useState({
    jobTitle: "Senior Software Engineer",
    seniority: "senior",
    location: "Bangalore, India",
    jobDescription:
      "We're hiring a Senior Software Engineer to lead backend development for our payments platform. You will design and build distributed services in Python/Go, mentor junior engineers, and partner with product to ship reliable financial infrastructure at scale.\n\nRequirements: 4+ years experience, strong system design skills, experience with PostgreSQL and event-driven architectures, comfort with on-call rotations.",
  });
  const [campaignId, setCampaignId] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function loadCampaigns() {
      try {
        const data = await campaignsApi.list({ page_size: 50 });
        if (!cancelled) {
          setCampaigns(data.results);
          if (data.results[0] && !campaignId) {
            setCampaignId(data.results[0].id);
          }
        }
      } catch (err) {
        console.error(err);
      }
    }
    loadCampaigns();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const search = async () => {
    if (!form.jobTitle.trim()) {
      toast.error("Job title is required");
      return;
    }
    setSearching(true);
    setSource(null);
    try {
      const response = await peopleApi.search({
        job_title: form.jobTitle.trim(),
        seniority_levels: [form.seniority],
        locations: form.location
          ? form.location.split(",").map((s) => s.trim()).filter(Boolean)
          : [],
        page: 1,
        per_page: 10,
      });
      setSource(response.source);
      const withSelection: SearchResult[] = response.candidates.map((c) => ({
        ...c,
        selected: true,
      }));
      setResults(withSelection);
      toast.success(
        `Found ${withSelection.length} candidate${
          withSelection.length === 1 ? "" : "s"
        } ${response.source === "mock" ? "(mock data)" : ""}`,
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Search failed");
    } finally {
      setSearching(false);
    }
  };

  const toggleSelect = (apolloId: string) => {
    setResults((prev) =>
      prev.map((c) =>
        c.apollo_id === apolloId ? { ...c, selected: !c.selected } : c,
      ),
    );
  };

  const importSelected = async () => {
    if (!campaignId) {
      toast.error("Select a campaign first");
      return;
    }
    const selected = results.filter((c) => c.selected);
    if (selected.length === 0) {
      toast.error("Select at least one candidate");
      return;
    }
    const withPhone = selected.filter(
      (c) => c.phone && /^\+[1-9]\d{1,14}$/.test(c.phone),
    );
    if (withPhone.length === 0) {
      toast.error("No selected candidates have a valid E.164 phone number");
      return;
    }
    setImporting(true);
    try {
      const data = await candidatesApi.bulkCreate({
        campaign_id: campaignId,
        candidates: withPhone.map((c) => ({
          campaign_id: campaignId,
          callee_name: c.name,
          mobile_number: c.phone,
          email: c.email || undefined,
          custom_data: {
            title: c.title,
            company: c.company,
            location: `${c.city}, ${c.country}`,
            linkedin: c.linkedin_url,
            apollo_id: c.apollo_id,
            seniority: c.seniority,
          },
        })),
      });
      setImported((prev) => prev + data.created);
      toast.success(`Imported ${data.created} candidate(s)`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Import failed");
    } finally {
      setImporting(false);
    }
  };

  const hasResults = results.length > 0;
  const selectedCount = results.filter((r) => r.selected).length;
  const reachedOut = imported > 0;
  const currentStep = !hasResults ? 1 : !reachedOut ? 2 : 3;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          People Search &amp; Reachout
        </h1>
        <p className="text-muted-foreground">
          Paste a job description, find candidates, and trigger AI-powered voice
          outreach in one flow
        </p>
      </div>

      <FlowStrip currentStep={currentStep} />

      <Card>
        <CardHeader>
          <div className="flex flex-col items-start justify-between gap-2 sm:flex-row sm:items-center">
            <div>
              <CardTitle>1. Describe the role</CardTitle>
              <CardDescription>
                Apollo.io searches by these signals — falls back to mock data
                when no API key is set
              </CardDescription>
            </div>
            {source === "mock" && (
              <Badge variant="secondary" className="shrink-0">
                Apollo mock dataset
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="jobDescription">Job description</Label>
            <Textarea
              id="jobDescription"
              placeholder="Paste the full job description here. The system will use the title and seniority to find matching candidates."
              value={form.jobDescription}
              onChange={(e) =>
                setForm({ ...form, jobDescription: e.target.value })
              }
              rows={4}
              className="resize-y"
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="jobTitle">Job title *</Label>
              <Input
                id="jobTitle"
                placeholder="Software Engineer"
                value={form.jobTitle}
                onChange={(e) =>
                  setForm({ ...form, jobTitle: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="seniority">Seniority</Label>
              <Select
                value={form.seniority}
                onValueChange={(v) => setForm({ ...form, seniority: v })}
              >
                <SelectTrigger id="seniority">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SENIORITY_OPTIONS.map((o) => (
                    <SelectItem key={o.value} value={o.value}>
                      {o.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="location">Location</Label>
              <Input
                id="location"
                placeholder="Bangalore, India"
                value={form.location}
                onChange={(e) =>
                  setForm({ ...form, location: e.target.value })
                }
              />
            </div>
          </div>
          <Button onClick={search} disabled={searching}>
            {searching ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Search className="mr-2 h-4 w-4" />
            )}
            {searching ? "Searching..." : "Search candidates"}
          </Button>
        </CardContent>
      </Card>

      {results.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex flex-col items-start justify-between gap-2 sm:flex-row sm:items-center">
              <div>
                <CardTitle>
                  2. Select candidates ({selectedCount} of {results.length}{" "}
                  selected)
                </CardTitle>
                <CardDescription>
                  Choose who to import into a campaign for AI voice reachout
                </CardDescription>
              </div>
              <div className="flex flex-col items-stretch gap-2 sm:flex-row sm:items-center">
                <Select value={campaignId} onValueChange={setCampaignId}>
                  <SelectTrigger className="min-w-[200px]">
                    <SelectValue placeholder="Choose campaign" />
                  </SelectTrigger>
                  <SelectContent>
                    {campaigns.length === 0 ? (
                      <SelectItem value="__none" disabled>
                        No campaigns yet
                      </SelectItem>
                    ) : (
                      campaigns.map((c) => (
                        <SelectItem key={c.id} value={c.id}>
                          {c.name}
                        </SelectItem>
                      ))
                    )}
                  </SelectContent>
                </Select>
                <Button
                  onClick={importSelected}
                  disabled={importing || results.filter((r) => r.selected).length === 0}
                >
                  {importing ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Download className="mr-2 h-4 w-4" />
                  )}
                  {importing
                    ? "Importing..."
                    : `Import selected (${results.filter((r) => r.selected).length})`}
                </Button>
              </div>
            </div>
            {imported > 0 && (
              <p className="mt-2 flex items-center gap-1 text-sm text-emerald-600">
                <CheckCircle2 className="h-4 w-4" />
                {imported} candidate{imported === 1 ? "" : "s"} imported so far
              </p>
            )}
          </CardHeader>
          <CardContent>
            {searching ? (
              <div className="space-y-2">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Skeleton key={i} className="h-16" />
                ))}
              </div>
            ) : (
              <div className="space-y-2">
                {results.map((c) => (
                  <label
                    key={c.apollo_id}
                    className="flex cursor-pointer items-start gap-3 rounded-md border p-3 hover:bg-accent"
                  >
                    <input
                      type="checkbox"
                      className="mt-1 h-4 w-4"
                      checked={c.selected}
                      onChange={() => toggleSelect(c.apollo_id)}
                    />
                    <div className="flex-1 space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium">{c.name}</p>
                        {c.phone ? (
                          <Badge variant="outline">Has phone</Badge>
                        ) : (
                          <Badge variant="destructive">No phone</Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {c.title} · {c.company}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {c.city}, {c.country} · {c.email || "no email"}
                      </p>
                    </div>
                    <UserPlus className="h-4 w-4 text-muted-foreground" />
                  </label>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {!searching && results.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center gap-3 py-12 text-center">
            <Users className="h-10 w-10 text-muted-foreground" />
            <p className="text-muted-foreground">
              Run a search to see candidates here.
            </p>
          </CardContent>
        </Card>
      )}

      {reachedOut && (
        <Card className="border-emerald-200 bg-emerald-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-emerald-800">
              <CheckCircle2 className="h-5 w-5" />
              3. AI reachout queued
            </CardTitle>
            <CardDescription className="text-emerald-700">
              {imported} candidate{imported === 1 ? "" : "s"} imported. Hunar
              will call each one and stream structured results to the Results
              page.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="outline">
              <a href="/results">View results →</a>
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function FlowStrip({ currentStep }: { currentStep: 1 | 2 | 3 }) {
  const steps = [
    { n: 1, label: "Describe role", icon: Search },
    { n: 2, label: "Select candidates", icon: UserPlus },
    { n: 3, label: "AI reachout", icon: PhoneCall },
  ] as const;
  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_auto_1fr_auto_1fr] sm:items-center">
      {steps.map((s, idx) => {
        const Icon = s.icon;
        const isDone = currentStep > s.n;
        const isActive = currentStep === s.n;
        return (
          <div key={s.n} className="contents">
            <div
              className={`flex items-center gap-3 rounded-md border p-3 transition-colors ${
                isActive
                  ? "border-primary bg-primary/5"
                  : isDone
                    ? "border-emerald-200 bg-emerald-50"
                    : "border-muted bg-muted/30"
              }`}
            >
              <div
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold ${
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : isDone
                      ? "bg-emerald-600 text-white"
                      : "bg-muted text-muted-foreground"
                }`}
              >
                {isDone ? <CheckCircle2 className="h-4 w-4" /> : s.n}
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium leading-tight">{s.label}</p>
                <p className="text-xs text-muted-foreground">
                  {isActive ? "In progress" : isDone ? "Complete" : "Pending"}
                </p>
              </div>
              <Icon
                className={`h-4 w-4 ${
                  isActive
                    ? "text-primary"
                    : isDone
                      ? "text-emerald-600"
                      : "text-muted-foreground"
                }`}
              />
            </div>
            {idx < steps.length - 1 && (
              <ArrowRight
                className={`mx-auto h-4 w-4 ${
                  currentStep > s.n
                    ? "text-emerald-600"
                    : "text-muted-foreground"
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

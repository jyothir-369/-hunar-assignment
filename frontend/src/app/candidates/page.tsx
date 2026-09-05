"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Plus, Search, Users } from "lucide-react";
import Link from "next/link";

import { candidatesApi } from "@/lib/api";
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
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
import {
  CALL_STATUS_COLORS,
  CALL_STATUSES,
  type CallStatus,
  type Candidate,
} from "@/types";

export default function CandidatesPage() {
  const router = useRouter();
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [search, setSearch] = useState("");

  // Add-candidate dialog state
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    campaign_id: "",
    callee_name: "",
    mobile_number: "+91",
    email: "",
  });

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const params: { page_size: number; status?: string } = {
          page_size: 100,
        };
        if (statusFilter !== "all") params.status = statusFilter;
        const data = await candidatesApi.list(params);
        if (!cancelled) setCandidates(data.results);
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
  }, [statusFilter]);

  async function handleAdd() {
    if (!form.campaign_id || !form.callee_name || !form.mobile_number) {
      toast.error("Campaign id, name, and phone are required");
      return;
    }
    if (!/^\+[1-9]\d{1,14}$/.test(form.mobile_number)) {
      toast.error("Phone must be E.164 format, e.g. +919876543210");
      return;
    }
    setSubmitting(true);
    try {
      const created = await candidatesApi.create({
        campaign_id: form.campaign_id,
        callee_name: form.callee_name,
        mobile_number: form.mobile_number,
        email: form.email || undefined,
        custom_data: {},
      });
      setCandidates((prev) => [created, ...prev]);
      toast.success("Candidate added");
      setForm({
        campaign_id: form.campaign_id,
        callee_name: "",
        mobile_number: "+91",
        email: "",
      });
      setOpen(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to add candidate");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this candidate?")) return;
    try {
      await candidatesApi.delete(id);
      setCandidates((prev) => prev.filter((c) => c.id !== id));
      toast.success("Candidate removed");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete");
    }
  }

  const filtered = candidates.filter((c) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      c.callee_name.toLowerCase().includes(q) ||
      c.mobile_number.includes(search) ||
      (c.email ?? "").toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Candidates</h1>
          <p className="text-muted-foreground">
            All candidates across your campaigns
          </p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" /> Add candidate
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add candidate</DialogTitle>
              <DialogDescription>
                Append a single candidate to an existing campaign.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-3">
              <div className="space-y-1">
                <Label htmlFor="c-campaign">Campaign id *</Label>
                <Input
                  id="c-campaign"
                  placeholder="uuid"
                  value={form.campaign_id}
                  onChange={(e) =>
                    setForm({ ...form, campaign_id: e.target.value })
                  }
                />
                <p className="text-xs text-muted-foreground">
                  Find this on the campaigns page.
                </p>
              </div>
              <div className="space-y-1">
                <Label htmlFor="c-name">Name *</Label>
                <Input
                  id="c-name"
                  value={form.callee_name}
                  onChange={(e) =>
                    setForm({ ...form, callee_name: e.target.value })
                  }
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="c-phone">Mobile (E.164) *</Label>
                <Input
                  id="c-phone"
                  value={form.mobile_number}
                  onChange={(e) =>
                    setForm({ ...form, mobile_number: e.target.value })
                  }
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="c-email">Email</Label>
                <Input
                  id="c-email"
                  type="email"
                  value={form.email}
                  onChange={(e) =>
                    setForm({ ...form, email: e.target.value })
                  }
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleAdd} disabled={submitting}>
                {submitting ? "Adding..." : "Add candidate"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <div className="relative max-w-sm flex-1">
          <Search className="text-muted-foreground absolute left-2.5 top-2.5 h-4 w-4" />
          <Input
            placeholder="Search by name, phone, email"
            className="pl-8"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[200px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {CALL_STATUSES.map((s) => (
              <SelectItem key={s} value={s}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {error && (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="pt-6 text-sm text-destructive">
            {error}
          </CardContent>
        </Card>
      )}

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-16" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center gap-4 py-12 text-center">
            <Users className="h-10 w-10 text-muted-foreground" />
            <div>
              <p className="font-medium">
                {candidates.length === 0
                  ? "No candidates yet"
                  : "No candidates match your filters"}
              </p>
              <p className="text-sm text-muted-foreground">
                {candidates.length === 0
                  ? "Upload a CSV or import from People Search to start building your talent pool."
                  : "Try clearing the search box or the status filter."}
              </p>
            </div>
            {candidates.length === 0 ? (
              <div className="flex flex-wrap items-center justify-center gap-2">
                <Button asChild>
                  <Link href="/people">Search candidates on Apollo</Link>
                </Button>
                <Button asChild variant="outline">
                  <Link href="/campaigns">View campaigns</Link>
                </Button>
              </div>
            ) : (
              <Button
                variant="outline"
                onClick={() => {
                  setSearch("");
                  setStatusFilter("all");
                }}
              >
                Clear filters
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>
              {filtered.length} candidate{filtered.length === 1 ? "" : "s"}
            </CardTitle>
            <CardDescription>
              Click a row to open the campaign it belongs to
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {filtered.map((c) => {
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
                      <p className="text-xs text-muted-foreground">
                        Campaign:{" "}
                        <button
                          type="button"
                          onClick={() => router.push(`/campaigns/${c.campaign_id}`)}
                          className="font-mono text-primary hover:underline"
                        >
                          {c.campaign_id.slice(0, 8)}…
                        </button>
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
          </CardContent>
        </Card>
      )}
    </div>
  );
}

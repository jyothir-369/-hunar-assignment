"use client";

import {
  ArrowRight,
  Building2,
  Calendar,
  CheckCircle2,
  CircuitBoard,
  Cpu,
  Database,
  FileText,
  Fingerprint,
  Hash,
  MessageSquare,
  PhoneCall,
  ShieldCheck,
  Smartphone,
  Users,
  Workflow,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const FLOW_NODES = [
  {
    n: 1,
    label: "Employee",
    sub: "No smartphone, no app",
    icon: Users,
    tone: "border-muted bg-muted/30",
    iconTone: "bg-muted text-muted-foreground",
  },
  {
    n: 2,
    label: "Local phone / landline / kiosk",
    sub: "Voice, IVR, SMS, biometric, RFID",
    icon: PhoneCall,
    tone: "border-blue-200 bg-blue-50",
    iconTone: "bg-blue-100 text-blue-700",
  },
  {
    n: 3,
    label: "Location identifier",
    sub: "Each site has a stable id",
    icon: Hash,
    tone: "border-muted bg-muted/30",
    iconTone: "bg-muted text-muted-foreground",
  },
  {
    n: 4,
    label: "Attendance gateway",
    sub: "Ingests all channels",
    icon: CircuitBoard,
    tone: "border-violet-200 bg-violet-50",
    iconTone: "bg-violet-100 text-violet-700",
  },
  {
    n: 5,
    label: "LLM reconciliation",
    sub: "Reasons across sources, flags anomalies",
    icon: Cpu,
    tone: "border-amber-200 bg-amber-50",
    iconTone: "bg-amber-100 text-amber-700",
  },
  {
    n: 6,
    label: "Centralised attendance ledger",
    sub: "One source of truth, per-employee",
    icon: Database,
    tone: "border-slate-200 bg-slate-50",
    iconTone: "bg-slate-200 text-slate-700",
  },
  {
    n: 7,
    label: "HR dashboard",
    sub: "Real-time, plain-English summary",
    icon: Workflow,
    tone: "border-emerald-200 bg-emerald-50",
    iconTone: "bg-emerald-100 text-emerald-700",
  },
] as const;

const CHANNELS = [
  {
    name: "Outbound AI voice call",
    icon: PhoneCall,
    share: "~70% after rollout",
    summary:
      "Hunar places a 10–20 second call at shift start. The LLM does speaker verification, anti-spoofing, intent classification. Default channel — the system calls the employee, not the other way around.",
    where: "Every site, every employee with a phone number on file.",
  },
  {
    name: "Biometric / RFID kiosk",
    icon: Fingerprint,
    share: "~20% (high-headcount sites)",
    summary:
      "Fingerprint or face kiosk at factory gates; RFID badge readers in warehouses. Zero employee action, hard-to-forge identity. Spend hardware budget on the 20% of sites that hold 80% of headcount.",
    where: "Large factories, secure sites, warehouses.",
  },
  {
    name: "SMS / IVR pull channel",
    icon: MessageSquare,
    share: "~8%",
    summary:
      "Free inbound IVR number (punch in employee ID + voice OTP) and structured SMS (`P 12 4` = present 12, absent 4). LLM parses free-form replies into structured rows.",
    where: "Small sites, late arrivals, sick leave notifications.",
  },
  {
    name: "Supervisor fallback",
    icon: ShieldCheck,
    share: "~2%",
    summary:
      "Supervisor confirms shift attendance from a shared tablet or laptop (company device, not personal). Queues offline and uploads when signal returns. The LLM reconciles supervisor confirmations against individual check-ins.",
    where: "Remote sites, edge cases, dispute resolution.",
  },
] as const;

const DAILY_OUTPUT = [
  "A per-employee verdict: present / absent / late / leave / unverified, with a confidence score.",
  "A short, plain-English summary for HR — '988 present, 9 absent (4 with approved leave), 3 unverified. Exception: Aarav Sharma — voice said present from a number not on file, no biometric match at the gate, supervisor marked absent. Recommend manual review.'",
  "A weekly payroll-ready export that handles partial days, late arrivals, overtime, and the inevitable 'I was there but the system didn't see me' cases.",
  "Anomaly flags: buddy-punching, geo-impossibility, pattern anomalies (always-late-Monday, etc.).",
];

export default function AttendancePage() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Badge variant="secondary" className="gap-1">
            <Building2 className="h-3 w-3" /> Problem 3
          </Badge>
          <Badge variant="outline">Conceptual architecture</Badge>
        </div>
        <h1 className="text-3xl font-bold tracking-tight">
          Attendance Without Smartphones
        </h1>
        <p className="text-muted-foreground max-w-3xl">
          Track daily attendance of 1,000 employees across 100 sites using only
          the channels available without a personal smartphone: voice, IVR,
          SMS, supervisor confirmation, and shared site hardware. Every channel
          feeds the same ledger; the LLM is the reasoning layer that makes the
          messy multi-source reality usable for HR.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Workflow className="h-5 w-5" /> End-to-end architecture
          </CardTitle>
          <CardDescription>
            The data path: employee → local device → gateway → LLM reconciliation
            → ledger → HR.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-4">
            {FLOW_NODES.map((node, idx) => {
              const Icon = node.icon;
              return (
                <div key={node.n} className="relative">
                  <div
                    className={`flex h-full flex-col gap-2 rounded-md border p-3 ${node.tone}`}
                  >
                    <div className="flex items-center gap-2">
                      <div
                        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md ${node.iconTone}`}
                      >
                        <Icon className="h-4 w-4" />
                      </div>
                      <p className="text-sm font-semibold">
                        {node.n}. {node.label}
                      </p>
                    </div>
                    <p className="text-xs text-muted-foreground">{node.sub}</p>
                  </div>
                  {idx < FLOW_NODES.length - 1 && (
                    <ArrowRight
                      className="absolute -right-2 top-1/2 hidden h-4 w-4 -translate-y-1/2 text-muted-foreground lg:block"
                      aria-hidden
                    />
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Cpu className="h-5 w-5" /> Multi-channel design
          </CardTitle>
          <CardDescription>
            Any single channel can fail. The system survives because every
            channel writes to the same ledger and the LLM reconciles across
            them.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {CHANNELS.map((c) => {
            const Icon = c.icon;
            return (
              <div
                key={c.name}
                className="flex flex-col gap-2 rounded-md border p-3 sm:flex-row sm:items-start sm:gap-4"
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
                  <Icon className="h-4 w-4" />
                </div>
                <div className="flex-1 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-medium">{c.name}</p>
                    <Badge variant="outline" className="text-xs">
                      {c.share}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">{c.summary}</p>
                  <p className="text-xs text-muted-foreground">
                    <span className="font-medium text-foreground">Where:</span>{" "}
                    {c.where}
                  </p>
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" /> What the LLM produces each day
            </CardTitle>
            <CardDescription>
              The single most valuable thing the LLM does is the daily
              reconciliation pass.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              {DAILY_OUTPUT.map((line) => (
                <li key={line} className="flex items-start gap-2">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                  <span className="text-muted-foreground">{line}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5" /> Privacy &amp; defensibility
            </CardTitle>
            <CardDescription>
              When an employee asks "why was I marked absent?" the system has
              to answer.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>
              <span className="font-medium text-foreground">
                Collect only what's needed.
              </span>{" "}
              Store short summaries, not full audio — unless an exception
              requires drilling in.
            </p>
            <p>
              <span className="font-medium text-foreground">
                Explain every decision.
              </span>{" "}
              Click a row, see the chain of evidence: which channel, which
              timestamp, which confidence.
            </p>
            <p>
              <span className="font-medium text-foreground">
                Opt-in with a real alternative.
              </span>{" "}
              IVR/SMS path is no-record-by-default. People are not penalised
              for choosing the lower-fidelity channel.
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" /> 30-day rollout plan
          </CardTitle>
          <CardDescription>
            A path that works on day one and gets better over time.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              {
                week: "Week 1",
                title: "Voice channel",
                body: "Stand up outbound AI calling — a thin wrapper around the same Hunar integration used in the hiring product. One campaign per day, one question per employee.",
              },
              {
                week: "Week 2",
                title: "SMS + supervisor fallback",
                body: "Add the inbound IVR number and the supervisor SMS path. Most 'missed call' cases get resolved here.",
              },
              {
                week: "Week 3",
                title: "Hardware pilot",
                body: "Buy 5–10 biometric kiosks, deploy at the largest sites. Confirm they work, confirm the data flows, confirm the LLM reconciliation handles the new source.",
              },
              {
                week: "Week 4",
                title: "Reconciliation + reporting",
                body: "Turn on the LLM reconciliation pass. Ship the HR dashboard with the plain-English daily summary and the per-employee audit trail.",
              },
            ].map((step) => (
              <div key={step.week} className="rounded-md border p-3">
                <p className="text-xs font-semibold uppercase text-muted-foreground">
                  {step.week}
                </p>
                <p className="text-sm font-medium">{step.title}</p>
                <p className="mt-1 text-xs text-muted-foreground">{step.body}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="border-dashed">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Smartphone className="h-4 w-4" /> Read the full design brief
          </CardTitle>
          <CardDescription>
            The repo includes a 10-section design document with channel-mix
            estimates, edge cases, and the case for an LLM over a rules
            engine.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild variant="outline">
            <a
              href="https://github.com/jyothir-369/hunar-assignment/blob/main/PROBLEM3.md"
              target="_blank"
              rel="noopener noreferrer"
            >
              Open PROBLEM3.md →
            </a>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  BarChart3,
  Bot,
  Building2,
  LayoutDashboard,
  Megaphone,
  Radio,
  Search,
  Settings,
  Sparkles,
  Users,
} from "lucide-react";

import { settingsApi, type RuntimeSettings } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

const items = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/campaigns", label: "Campaigns", icon: Megaphone },
  { href: "/candidates", label: "Candidates", icon: Users },
  { href: "/people", label: "People Search", icon: Search },
  { href: "/attendance", label: "Attendance", icon: Building2 },
  { href: "/results", label: "Results", icon: BarChart3 },
  { href: "/settings", label: "Settings", icon: Settings },
] as const;

export function AppSidebar() {
  const pathname = usePathname();
  // null = loading, true = demo, false = live
  const [demoMode, setDemoMode] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    settingsApi
      .get()
      .then((s: RuntimeSettings) => {
        if (!cancelled) setDemoMode(Boolean(s.demo?.seeded));
      })
      .catch(() => {
        if (!cancelled) setDemoMode(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <aside className="hidden md:flex w-64 shrink-0 flex-col border-r bg-card">
      <div className="border-b p-6">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Bot className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-base font-semibold leading-tight">
              Hunar Hiring
            </h1>
            <p className="text-xs text-muted-foreground">AI Voice Assistant</p>
          </div>
        </Link>
      </div>

      <nav className="flex-1 space-y-1 p-3">
        {items.map((item) => {
          const Icon = item.icon;
          // For nested routes, highlight the longest matching parent
          const active =
            item.href === "/"
              ? pathname === "/"
              : pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t p-4 text-xs text-muted-foreground space-y-2">
        <div className="flex items-center gap-2">
          {demoMode === null ? (
            <Badge variant="outline" className="text-[10px] uppercase tracking-wide">
              Checking…
            </Badge>
          ) : demoMode ? (
            <Badge
              variant="secondary"
              className="gap-1 bg-amber-100 text-amber-900 border-amber-200"
              title="Database contains the 'Demo Recruiter Agent' marker. Results are synthetic but representative of the full flow."
            >
              <Sparkles className="h-3 w-3" /> Demo Environment
            </Badge>
          ) : (
            <Badge
              variant="outline"
              className="gap-1 border-emerald-200 bg-emerald-50 text-emerald-700"
              title="No demo marker found — data shown reflects real activity only."
            >
              <Radio className="h-3 w-3" /> Live
            </Badge>
          )}
        </div>
        <div>
          <p className="font-medium">Hunar AI Hiring</p>
          <p>v1.0.0</p>
        </div>
      </div>
    </aside>
  );
}

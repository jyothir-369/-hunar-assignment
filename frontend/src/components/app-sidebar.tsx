"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Bot,
  Building2,
  LayoutDashboard,
  Megaphone,
  Search,
  Settings,
  Users,
} from "lucide-react";

import { cn } from "@/lib/utils";

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

      <div className="border-t p-4 text-xs text-muted-foreground">
        <p className="font-medium">Hunar AI Hiring</p>
        <p>v1.0.0</p>
      </div>
    </aside>
  );
}

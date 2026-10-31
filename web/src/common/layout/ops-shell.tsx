"use client";

import {
  Bot,
  Calendar,
  ChartLine,
  FileText,
  Flag,
  House,
  LayoutGrid,
  List,
  Scale,
  Shield,
  Store,
  Users,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { cn } from "../ui/cn";
import { Avatar } from "../ui/surfaces";
import { Wordmark } from "../ui/wordmark";
import { isActive, OPS_NAV, shown } from "./nav";

// Ops console shell (components.md: Ops sidebar), desktop 1440 only. The global search and "session time
// left" are hidden: there is no search endpoint, and the backend has no ops session limit yet (the design's
// 8 h is a placeholder).

export type QueueCounts = { vetting: number; flagged_evidence: number; disputes: number };

const ICONS: Record<string, LucideIcon> = {
  Overview: LayoutGrid,
  Vetting: Shield,
  "Flagged evidence": Flag,
  Disputes: Scale,
  Projects: House,
  "Spot checks": Calendar,
  Suppliers: Store,
  "Price index": ChartLine,
  "Weekly reports": FileText,
  "Audit log": List,
  "Agent runs": Bot,
  Users,
};

export function OpsSidebar({
  name,
  counts,
  showAll = false,
}: {
  name: string;
  counts: QueueCounts | null;
  showAll?: boolean;
}) {
  const pathname = usePathname();
  return (
    <aside className="ibh-on-navy flex w-58 flex-none flex-col bg-navy-900 text-navy-200">
      <Link
        href="/ops"

        className="flex items-center gap-2 px-4.5 py-4"
      >
        <Wordmark onDark />
        <span className="type-caption rounded-tag bg-navy-700 px-1.5 text-white">OPS</span>
      </Link>
      <nav aria-label="Ops console" className="flex flex-1 flex-col gap-1 overflow-y-auto px-2.5 pb-4">
        {OPS_NAV.map((section, i) => {
          const items = shown(section.items, showAll);
          if (!items.length) return null;
          return (
            <div key={section.heading ?? i} className="flex flex-col gap-0.5">
              {section.heading ? (
                <p className="type-caption px-2.5 pt-4 pb-1.5 text-x-on-navy-muted uppercase">
                  {section.heading}
                </p>
              ) : null}
              <ul className="flex flex-col gap-0.5">
                {items.map((item) => {
                  const Icon = ICONS[item.label] ?? LayoutGrid;
                  const active = item.href === "/ops" ? pathname === "/ops" : isActive(pathname, item.href);
                  const count = item.queue && counts ? counts[item.queue] : 0;
                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        aria-current={active ? "page" : undefined}
                        className={cn(
                          "type-small flex min-h-9 items-center gap-3 rounded-control px-2.5",
                          "",
                          active
                            ? "border-l-2 border-focus-on-dark bg-navy-700 font-semibold text-white"
                            : "hover:bg-navy-800 hover:text-white",
                        )}
                      >
                        <Icon aria-hidden strokeWidth={1.75} className="size-4.5 flex-none" />
                        <span className="flex-1">{item.label}</span>
                        {count ? (
                          <span className="type-caption min-w-5 rounded-pill bg-white px-1.5 text-center tracking-normal text-navy-900">
                            {count}
                            <span className="sr-only"> waiting</span>
                          </span>
                        ) : null}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </nav>
      <Link
        href="/ops/profile"
        aria-label={`${name}, your profile`}
        className="flex items-center gap-3 border-t border-navy-700 px-4.5 py-4 hover:bg-navy-800"
      >
        <Avatar name={name} size={32} className="bg-navy-700 text-white" />
        <div className="flex flex-col">
          <span className="type-small font-semibold text-white">{name}</span>
          <span className="type-caption tracking-normal text-x-on-navy-muted">Operations · Your profile</span>
        </div>
      </Link>
    </aside>
  );
}

const ENV_LABEL: Record<string, string> = { local: "LOCAL", staging: "STAGING", production: "PRODUCTION" };

/** The page title bar: title, then the environment badge so nobody mistakes staging for production. */
export function OpsHeader({
  title,
  environment,
  actions,
}: {
  title: string;
  environment: string;
  actions?: ReactNode;
}) {
  return (
    <header className="flex h-13 items-center gap-4 border-b border-line bg-white px-5">
      <h1 className="type-h3 text-ink">{title}</h1>
      <div className="ml-auto flex items-center gap-3">
        {actions}
        <span className="type-caption rounded-tag bg-mist px-2.5 py-1 text-slate">
          {ENV_LABEL[environment] ?? environment.toUpperCase()}
        </span>
      </div>
    </header>
  );
}

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "../ui/cn";
import { StatusChip } from "../ui/status-chip";
import { Wordmark } from "../ui/wordmark";
import { AvatarMenu } from "./avatar-menu";
import { CONTRACTOR_NAV, CONTRACTOR_PROJECT_TABS, isActive, shown } from "./nav";

// Contractor top bar (components.md: ConTop): wordmark with a "Contractor" tag, Projects / Orders / Payouts /
// Profile, and the person. The project row under it (back link, title, project tabs) comes with the project
// screens (ContractorProjectHeader). Help and the bell are hidden until their pages exist.

export function ContractorTop({ name, showAll = false }: { name: string; showAll?: boolean }) {
  const pathname = usePathname();
  const items = shown(CONTRACTOR_NAV, showAll);
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-white">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-4 px-4 sm:gap-8 sm:px-8">
        <Link href="/c" className="flex items-center gap-2 rounded-control">
          <Wordmark />
          <span className="type-caption hidden rounded-tag bg-mist px-2 py-0.5 font-semibold tracking-normal text-slate sm:inline">
            Contractor
          </span>
        </Link>
        <nav aria-label="Main" className="flex h-full">
          <ul className="flex h-full gap-1">
            {items.map((item) => {
              const active =
                item.href === "/c"
                  ? pathname === "/c" || pathname.startsWith("/c/projects")
                  : isActive(pathname, item.href);
              return (
                <li key={item.href} className="flex">
                  <Link
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "type-small flex items-center border-b-2 px-3",
                      "",
                      active
                        ? "border-navy-900 font-semibold text-ink"
                        : "border-transparent text-slate hover:text-ink",
                    )}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        <div className="ml-auto">
          <AvatarMenu name={name} />
        </div>
      </div>
    </header>
  );
}

/** The project row under the top bar: back to Projects, the title and status, then the project tabs. The design's
 *  "Client: name" waits for names on the project (MX-26). */
export function ContractorProjectHeader({
  id,
  title,
  status,
  showAll = false,
}: {
  id: string;
  title: string;
  status: string;
  showAll?: boolean;
}) {
  const pathname = usePathname();
  const tabs = shown(CONTRACTOR_PROJECT_TABS, showAll);
  return (
    <div className="border-b border-line bg-white">
      <div className="mx-auto w-full max-w-7xl px-4 pt-4 sm:px-10">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <Link href="/c" className="type-small rounded-control font-semibold text-accent">
            ‹ Projects
          </Link>
          <h1 className="type-h2 text-ink">{title}</h1>
          <StatusChip entity="project" state={status} audience="contractor" />
        </div>
        <nav aria-label="Project sections" className="mt-2">
          <ul className="flex gap-1 overflow-x-auto">
            {tabs.map((tab) => {
              const href = `/c/projects/${id}${tab.path}`;
              const active = isActive(pathname, href);
              return (
                <li key={tab.label}>
                  <Link
                    href={href}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "type-small flex min-h-target items-center border-b-2 px-3.5 whitespace-nowrap",
                      active
                        ? "border-navy-900 font-semibold text-ink"
                        : "border-transparent text-slate hover:text-ink",
                    )}
                  >
                    {tab.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </div>
    </div>
  );
}

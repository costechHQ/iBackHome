"use client";

import * as Menu from "@radix-ui/react-dropdown-menu";
import { Camera, ChevronDown, FileText, House, Layers, Wallet, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { cn } from "../ui/cn";
import { StatusChip } from "../ui/status-chip";
import { Mark, Wordmark } from "../ui/wordmark";
import { AvatarMenu } from "./avatar-menu";
import { CLIENT_MOBILE_NAV, CLIENT_PROJECT_TABS, isActive, shown } from "./nav";

// The client portal shell (components.md: ClientTop, ClientTabs, ClientNav). Help and the notifications bell
// are hidden until their pages exist (Help centre, WEB-CLIENT-020 + MX-11).

export type ProjectSummary = { id: string; title: string };

function ProjectSwitcher({
  projects,
  currentId,
}: {
  projects: readonly ProjectSummary[];
  currentId?: string;
}) {
  const current = projects.find((p) => p.id === currentId);
  if (!projects.length) return null;
  return (
    <Menu.Root>
      <Menu.Trigger className="type-small flex min-h-target max-w-56 items-center gap-2 rounded-control bg-mist px-3 font-semibold text-ink hover:bg-placeholder sm:max-w-72">
        <span className="truncate">{current?.title ?? "Your projects"}</span>
        <span className="sr-only">, switch project</span>
        <ChevronDown aria-hidden strokeWidth={1.75} className="size-4 flex-none" />
      </Menu.Trigger>
      <Menu.Portal>
        <Menu.Content
          align="start"
          sideOffset={6}
          className="z-50 max-h-96 min-w-64 overflow-y-auto rounded-card border border-line bg-white p-1 shadow-raised"
        >
          <Menu.RadioGroup value={currentId ?? ""}>
            {projects.map((p) => (
              <Menu.RadioItem key={p.id} value={p.id} asChild>
                <Link
                  href={`/projects/${p.id}`}
                  className="type-small flex min-h-target items-center rounded-control px-3 text-ink outline-none aria-checked:font-semibold data-highlighted:bg-mist"
                >
                  {p.title}
                </Link>
              </Menu.RadioItem>
            ))}
          </Menu.RadioGroup>
          <Menu.Separator className="my-1 h-px bg-line" />
          <Menu.Item asChild>
            <Link
              href="/projects"
              className="type-small flex min-h-target items-center rounded-control px-3 font-semibold text-accent outline-none data-highlighted:bg-mist"
            >
              All projects
            </Link>
          </Menu.Item>
        </Menu.Content>
      </Menu.Portal>
    </Menu.Root>
  );
}

/** ClientTop: 64px desktop, 56px mobile. */
export function ClientTop({ name, projects }: { name: string; projects: readonly ProjectSummary[] }) {
  const params = useParams<{ id?: string }>();
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-white">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-4 sm:h-16 sm:gap-6 sm:px-8">
        <Link href="/projects" aria-label="iBackHome, your projects" className="rounded-control">
          <Wordmark className="hidden sm:inline-flex" />
          <Mark className="sm:hidden" />
        </Link>
        <ProjectSwitcher projects={projects} currentId={params.id} />
        <div className="ml-auto">
          <AvatarMenu name={name} />
        </div>
      </div>
    </header>
  );
}

/** Project title row and the project tabs (desktop). Badges count things that need the client. */
export function ProjectHeader({
  id,
  title,
  status,
  address,
  badges = {},
  showAll = false,
}: {
  id: string;
  title: string;
  status: string;
  address: string;
  badges?: Partial<Record<(typeof CLIENT_PROJECT_TABS)[number]["label"], number>>;
  showAll?: boolean;
}) {
  const pathname = usePathname();
  const tabs = shown(CLIENT_PROJECT_TABS, showAll);
  return (
    <div className="mx-auto w-full max-w-7xl px-4 pt-6 sm:px-10">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <h1 className="type-h2 text-ink">{title}</h1>
        <StatusChip entity="project" state={status} audience="client" />
        <p className="type-small text-slate">{address}</p>
      </div>
      {tabs.length ? (
        <nav aria-label="Project" className="mt-4 hidden border-b border-line sm:block">
          <ul className="flex gap-1 overflow-x-auto">
            {tabs.map((tab) => {
              const href = `/projects/${id}${tab.path}`;
              const active = tab.path ? isActive(pathname, href) : pathname === href;
              const badge = badges[tab.label];
              return (
                <li key={tab.label}>
                  <Link
                    href={href}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "type-small flex min-h-target items-center gap-2 border-b-2 px-3.5 whitespace-nowrap",
                      "",
                      active
                        ? "border-navy-900 font-semibold text-ink"
                        : "border-transparent text-slate hover:text-ink",
                    )}
                  >
                    {tab.label}
                    {badge ? (
                      <span className="type-caption rounded-pill bg-navy-900 px-1.5 tracking-normal text-white">
                        {badge}
                        <span className="sr-only"> need your attention</span>
                      </span>
                    ) : null}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      ) : null}
    </div>
  );
}

const MOBILE_ICONS: Record<(typeof CLIENT_MOBILE_NAV)[number]["label"], LucideIcon> = {
  Home: House,
  Milestones: Layers,
  Evidence: Camera,
  Money: Wallet,
  Reports: FileText,
};

/** ClientNav: the mobile bottom bar (72px). The active item differs by weight and a tinted pill, not colour alone. */
export function ClientNav({
  showAll = false,
  badges = {},
}: {
  showAll?: boolean;
  badges?: Partial<Record<string, number>>;
}) {
  const pathname = usePathname();
  const params = useParams<{ id?: string }>();
  const items = shown(CLIENT_MOBILE_NAV, showAll).filter((i) => !i.projectScoped || params.id || showAll);
  if (items.length < 2) return null; // a bar with one item helps nobody
  return (
    <nav aria-label="Main" className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-white sm:hidden">
      <ul className="flex h-18 items-stretch justify-around px-2">
        {items.map((item) => {
          const href = item.projectScoped ? `/projects/${params.id ?? "_"}${item.path}` : item.path;
          const active = item.projectScoped ? isActive(pathname, href) : pathname === href;
          const Icon = MOBILE_ICONS[item.label];
          const badge = badges[item.label];
          return (
            <li key={item.label} className="flex flex-1">
              <Link
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "type-caption flex flex-1 flex-col items-center justify-center gap-1 tracking-normal",
                  "",
                  active ? "font-bold text-ink" : "font-medium text-slate",
                )}
              >
                <span
                  className={cn(
                    "relative flex h-8 w-14 items-center justify-center rounded-pill",
                    active && "bg-accent-tint",
                  )}
                >
                  <Icon aria-hidden strokeWidth={1.75} className="size-5" />
                  {badge ? (
                    <span className="type-caption absolute -top-1 right-2 rounded-pill bg-navy-900 px-1 tracking-normal text-white">
                      {badge}
                    </span>
                  ) : null}
                </span>
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

export function ClientMain({ children }: { children: ReactNode }) {
  // Room for the fixed bottom bar on mobile.
  return <main className="flex flex-1 flex-col bg-canvas pb-20 sm:pb-0">{children}</main>;
}

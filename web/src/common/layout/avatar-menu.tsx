"use client";

import * as Menu from "@radix-ui/react-dropdown-menu";
import { LogOut } from "lucide-react";

import { Avatar } from "../ui/surfaces";

// The initials pill at the right of every top bar ("CN Chioma"), opening a menu with sign-out. Settings joins
// it once its screen exists.

async function signOut() {
  await fetch("/api/session/sign-out", { method: "POST" }).catch(() => null);
  // A full page load drops every cached query of the person who just left.
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination
  window.location.assign("/sign-in");
}

export function AvatarMenu({ name, onDark }: { name: string; onDark?: boolean }) {
  const firstName = name.split(/\s+/)[0] ?? name;
  return (
    <Menu.Root>
      <Menu.Trigger
        className={
          onDark
            ? "flex min-h-target items-center gap-2 rounded-pill px-1 text-white"
            : "type-small flex min-h-target items-center gap-2 rounded-pill border border-line bg-white py-1 pr-3 pl-1 font-semibold text-ink hover:bg-mist"
        }
      >
        <Avatar name={name} size={32} />
        {/* The visible first name starts the accessible name (WCAG 2.5.3); on phones it is visually hidden. */}
        <span className="max-sm:sr-only">{firstName}</span>
        <span className="sr-only">, account menu</span>
      </Menu.Trigger>
      <Menu.Portal>
        <Menu.Content
          align="end"
          sideOffset={6}
          className="z-50 min-w-48 rounded-card border border-line bg-white p-1 shadow-raised"
        >
          <Menu.Label className="type-small px-3 py-2 text-muted">{name}</Menu.Label>
          <Menu.Item
            onSelect={() => void signOut()}
            className="type-small flex min-h-target cursor-pointer items-center gap-2 rounded-control px-3 font-semibold text-ink outline-none data-highlighted:bg-mist"
          >
            <LogOut aria-hidden strokeWidth={1.75} className="size-4" />
            Sign out
          </Menu.Item>
        </Menu.Content>
      </Menu.Portal>
    </Menu.Root>
  );
}

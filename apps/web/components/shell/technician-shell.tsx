"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { VehiclesIcon, WorkIcon } from "@/components/shell/icons";
import { NavLink, type NavItem } from "@/components/shell/nav-link";
import { UserMenu } from "@/components/shell/user-menu";
import type { User } from "@/types/auth";

const ITEMS: NavItem[] = [
  { href: "/my-work", label: "My work", icon: WorkIcon },
  { href: "/vehicles", label: "Vehicles", icon: VehiclesIcon },
];

/**
 * The technician shell: a work queue, not a console.
 *
 * No rail, two destinations, and a narrower column - a technician reads one
 * job at a time on a phone in a depot rather than scanning four hundred rows.
 * The fleet-wide screens are not hidden here so much as absent: the API
 * refuses them, and a shell that implied otherwise would be lying.
 */
export function TechnicianShell({
  user,
  children,
}: {
  user: User;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-full flex-col">
      <header className="bg-background sticky top-0 z-20 border-b">
        <div className="mx-auto flex w-full max-w-3xl items-center justify-between gap-3 px-4 py-2.5">
          <Link href="/my-work" className="flex items-center gap-2">
            <span className="bg-foreground size-4 rounded-sm" aria-hidden />
            <span className="text-sm font-semibold tracking-tight">
              Fleet Maintenance
            </span>
          </Link>
          <UserMenu user={user} />
        </div>

        <nav
          aria-label="Main"
          className="mx-auto flex w-full max-w-3xl gap-1 px-3 pb-2"
        >
          {ITEMS.map((item) => (
            <NavLink key={item.href} item={item} variant="bar" />
          ))}
        </nav>
      </header>

      <main id="content" className="flex-1 px-4 py-5">
        <div className="mx-auto w-full max-w-3xl">{children}</div>
      </main>
    </div>
  );
}

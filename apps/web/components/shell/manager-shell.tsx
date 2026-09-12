"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import {
  AlertsIcon,
  DashboardIcon,
  ReportsIcon,
  ServicesIcon,
  VehiclesIcon,
} from "@/components/shell/icons";
import { NavBadge, NavLink, type NavItem } from "@/components/shell/nav-link";
import { UserMenu } from "@/components/shell/user-menu";
import { useAlertCount } from "@/hooks/use-alerts";
import type { User } from "@/types/auth";

const ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: DashboardIcon },
  { href: "/vehicles", label: "Vehicles", icon: VehiclesIcon },
  { href: "/services", label: "Services", icon: ServicesIcon },
  { href: "/alerts", label: "Alerts", icon: AlertsIcon },
  { href: "/reports", label: "Reports", icon: ReportsIcon },
];

/**
 * The fleet manager console: a persistent rail on a wide screen, everything
 * fleet-wide one click away, and the alert count always in view.
 *
 * A technician gets a different shell entirely rather than this one with items
 * removed - see technician-shell.tsx.
 */
export function ManagerShell({
  user,
  children,
}: {
  user: User;
  children: ReactNode;
}) {
  const { data } = useAlertCount(true);
  const count = data?.count ?? 0;

  return (
    <div className="flex min-h-full">
      <aside className="bg-subtle hidden w-56 shrink-0 flex-col border-r lg:flex">
        <div className="flex h-12 items-center gap-2 border-b px-4">
          <span className="bg-foreground size-4 rounded-sm" aria-hidden />
          <span className="text-sm font-semibold tracking-tight">
            Fleet Maintenance
          </span>
        </div>

        <nav aria-label="Main" className="flex flex-col gap-0.5 p-2">
          {ITEMS.map((item) => (
            <NavLink
              key={item.href}
              item={item}
              variant="rail"
              badge={item.href === "/alerts" ? <NavBadge count={count} /> : null}
            />
          ))}
        </nav>

        <div className="mt-auto border-t p-2">
          <UserMenu user={user} className="justify-between" />
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Below lg the rail is gone, so the same five destinations scroll
            horizontally here rather than hiding behind a menu button. */}
        <header className="bg-background sticky top-0 z-20 border-b lg:hidden">
          <div className="flex h-12 items-center justify-between gap-3 px-4">
            <Link href="/dashboard" className="text-sm font-semibold">
              Fleet Maintenance
            </Link>
            <UserMenu user={user} />
          </div>
          <nav aria-label="Main" className="flex gap-1 overflow-x-auto px-2 pb-2">
            {ITEMS.map((item) => (
              <NavLink
                key={item.href}
                item={item}
                variant="bar"
                badge={
                  item.href === "/alerts" ? <NavBadge count={count} /> : null
                }
              />
            ))}
          </nav>
        </header>

        <main id="content" className="min-w-0 flex-1 px-4 py-5 lg:px-6 lg:py-6">
          <div className="mx-auto w-full max-w-[1400px]">{children}</div>
        </main>
      </div>
    </div>
  );
}

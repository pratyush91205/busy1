"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { useAlertCount } from "@/hooks/use-alerts";
import { useLogout } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";
import { ROLE_LABELS, type User } from "@/types/auth";

const LINKS = [
  { href: "/dashboard", label: "Dashboard", managerOnly: false },
  { href: "/vehicles", label: "Vehicles", managerOnly: false },
  { href: "/services", label: "Services", managerOnly: false },
  { href: "/alerts", label: "Alerts", managerOnly: true },
  { href: "/reports", label: "Reports", managerOnly: true },
];

export function AppHeader({ user }: { user: User }) {
  const router = useRouter();
  const pathname = usePathname();
  const logout = useLogout();

  const isManager = user.role === "fleet_manager";
  // Only a manager may read the count, so a technician never asks for it.
  const { data: alerts } = useAlertCount(isManager);
  const count = alerts?.count ?? 0;

  return (
    <header className="border-b">
      <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4 px-4 py-3">
        <div className="flex items-center gap-6">
          <span className="text-sm font-semibold">Fleet Maintenance</span>

          <nav className="flex items-center gap-4 text-sm">
            {LINKS.filter((link) => isManager || !link.managerOnly).map(
              ({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  className={cn(
                    "hover:text-foreground flex items-center gap-1.5 transition-colors",
                    pathname.startsWith(href)
                      ? "text-foreground font-medium"
                      : "text-muted-foreground",
                  )}
                >
                  {label}
                  {href === "/alerts" && count > 0 ? (
                    <span className="inline-flex min-w-5 items-center justify-center rounded-full bg-red-500/15 px-1.5 py-0.5 text-xs font-medium text-red-700 tabular-nums dark:text-red-300">
                      {count}
                      <span className="sr-only"> overdue service records</span>
                    </span>
                  ) : null}
                </Link>
              ),
            )}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right leading-tight">
            <p className="text-sm font-medium">{user.full_name}</p>
            {/* The role is shown because it explains which actions exist, not
                because the frontend decides anything with it. */}
            <p className="text-muted-foreground text-xs">
              {ROLE_LABELS[user.role]}
            </p>
          </div>

          <Button
            variant="ghost"
            onClick={() => {
              logout();
              router.replace("/login");
            }}
          >
            Sign out
          </Button>
        </div>
      </div>
    </header>
  );
}

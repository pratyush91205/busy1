"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { useLogout } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";
import { ROLE_LABELS, type User } from "@/types/auth";

const LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/vehicles", label: "Vehicles" },
];

export function AppHeader({ user }: { user: User }) {
  const router = useRouter();
  const pathname = usePathname();
  const logout = useLogout();

  return (
    <header className="border-b">
      <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4 px-4 py-3">
        <div className="flex items-center gap-6">
          <span className="text-sm font-semibold">Fleet Maintenance</span>

          <nav className="flex items-center gap-4 text-sm">
            {LINKS.map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                className={cn(
                  "hover:text-foreground transition-colors",
                  pathname.startsWith(href)
                    ? "text-foreground font-medium"
                    : "text-muted-foreground",
                )}
              >
                {label}
              </Link>
            ))}
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

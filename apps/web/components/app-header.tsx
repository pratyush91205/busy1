"use client";

import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { useLogout } from "@/hooks/use-auth";
import { ROLE_LABELS, type User } from "@/types/auth";

export function AppHeader({ user }: { user: User }) {
  const router = useRouter();
  const logout = useLogout();

  return (
    <header className="border-b">
      <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4 px-4 py-3">
        <span className="text-sm font-semibold">Fleet Maintenance</span>

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

"use client";

import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { useLogout } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";
import { ROLE_LABELS, type User } from "@/types/auth";

/**
 * Who is signed in, and the way out.
 *
 * The role is shown because it explains which actions exist on the screen,
 * not because the frontend decides anything with it.
 */
export function UserMenu({
  user,
  className,
}: {
  user: User;
  className?: string;
}) {
  const router = useRouter();
  const logout = useLogout();

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="min-w-0 leading-tight">
        <p className="truncate text-sm font-medium">{user.full_name}</p>
        <p className="text-muted-foreground truncate text-xs">
          {ROLE_LABELS[user.role]}
        </p>
      </div>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => {
          logout();
          router.replace("/login");
        }}
      >
        Sign out
      </Button>
    </div>
  );
}

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ComponentType, ReactNode } from "react";

import { cn } from "@/lib/utils";

export type NavItem = {
  href: string;
  label: string;
  icon: ComponentType<{ className?: string }>;
};

/** Active when it is the route, or an ancestor of it - /services/12 lights Services. */
export function useIsActive(href: string): boolean {
  const pathname = usePathname();
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function NavLink({
  item,
  badge,
  variant,
}: {
  item: NavItem;
  badge?: ReactNode;
  /** "rail" is the manager's sidebar; "bar" is the horizontal nav. */
  variant: "rail" | "bar";
}) {
  const active = useIsActive(item.href);
  const Icon = item.icon;

  return (
    <Link
      href={item.href}
      // aria-current is the accessible half of "you are here"; the colour is
      // the visual half, and neither stands alone.
      aria-current={active ? "page" : undefined}
      className={cn(
        "flex items-center gap-2 rounded-md text-sm transition-colors duration-120",
        variant === "rail" ? "px-2.5 py-1.5" : "px-2.5 py-1.5",
        active
          ? "bg-muted text-foreground font-medium"
          : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
      )}
    >
      <Icon className="size-4 shrink-0" />
      <span>{item.label}</span>
      {badge}
    </Link>
  );
}

/** The count beside Alerts. Rendered only when there is something to count. */
export function NavBadge({ count }: { count: number }) {
  if (count <= 0) return null;

  return (
    <span className="bg-overdue-soft text-overdue border-overdue/30 ml-auto inline-flex min-w-5 items-center justify-center rounded border px-1 py-0.5 text-[11px] font-semibold tabular-nums">
      {count}
      <span className="sr-only"> overdue service records</span>
    </span>
  );
}

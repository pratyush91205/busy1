"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCurrentUser, useLogin } from "@/hooks/use-auth";
import { landingRouteFor } from "@/lib/routes";

/**
 * Shape only. The server decides whether the credentials are real; this just
 * saves a round trip on an empty field.
 */
const loginSchema = z.object({
  email: z.email("Enter a valid email address"),
  password: z.string().min(1, "Enter your password"),
});

type LoginValues = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const login = useLogin();
  const { user } = useCurrentUser();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  // Covers both arriving here with a live session and the moment after a
  // successful submit. Where you land depends on the role: a manager onto the
  // fleet, a technician onto their own queue.
  useEffect(() => {
    if (user) router.replace(landingRouteFor(user));
  }, [user, router]);

  return (
    <main className="flex min-h-full items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center gap-2">
          <span className="bg-foreground size-4 rounded-sm" aria-hidden />
          <span className="text-sm font-semibold tracking-tight">
            Fleet Maintenance
          </span>
        </div>

        <div className="rounded-md border p-5">
          <header className="mb-5 space-y-1">
            <h1 className="text-base font-semibold">Sign in</h1>
            <p className="text-muted-foreground text-sm">
              Vehicles, service records and maintenance state for the fleet.
            </p>
          </header>

          <form
            onSubmit={handleSubmit((values) => login.mutate(values))}
            noValidate
            className="space-y-4"
          >
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="username"
                autoFocus
                className="h-9"
                aria-invalid={errors.email ? true : undefined}
                aria-describedby={errors.email ? "email-error" : undefined}
                {...register("email")}
              />
              {errors.email ? (
                <p id="email-error" className="text-destructive text-xs">
                  {errors.email.message}
                </p>
              ) : null}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                className="h-9"
                aria-invalid={errors.password ? true : undefined}
                aria-describedby={errors.password ? "password-error" : undefined}
                {...register("password")}
              />
              {errors.password ? (
                <p id="password-error" className="text-destructive text-xs">
                  {errors.password.message}
                </p>
              ) : null}
            </div>

            {/* The server's answer, verbatim: a wrong password and an
                unreachable API are different problems. */}
            {login.error ? (
              <p
                role="alert"
                className="border-destructive/40 bg-destructive/10 text-destructive rounded-md border px-3 py-2 text-sm"
              >
                {login.error.status === 401
                  ? "Those credentials were not accepted."
                  : login.error.message}
              </p>
            ) : null}

            <Button
              type="submit"
              className="h-9 w-full"
              disabled={login.isPending}
            >
              {login.isPending ? "Signing in…" : "Sign in"}
            </Button>
          </form>
        </div>
      </div>
    </main>
  );
}

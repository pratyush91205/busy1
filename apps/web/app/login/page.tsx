"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useEffect, useState, type KeyboardEvent } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ServiceCyclePreview } from "@/components/login/service-cycle-preview";
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

/**
 * The seeded demo accounts from scripts/seed_demo.py, so a reviewer can get in
 * with one click. They are public by design - SUBMISSION.md lists them - and
 * knowing them grants nothing beyond what the server already allows that role.
 * Never put a real account here: this ships in the browser bundle.
 */
const DEMO_ACCOUNTS = [
  { role: "Fleet manager", email: "manager@fleet.example", password: "demo1234" },
  { role: "Technician", email: "tech@fleet.example", password: "demo1234" },
] as const;

export default function LoginPage() {
  const router = useRouter();
  const login = useLogin();
  const { user } = useCurrentUser();
  const [showPassword, setShowPassword] = useState(false);
  const [capsLock, setCapsLock] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
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

  function signInAs(account: (typeof DEMO_ACCOUNTS)[number]) {
    const values = { email: account.email, password: account.password };
    // Fill the form as well, so a refusal shows what was sent.
    reset(values);
    login.mutate(values);
  }

  function trackCapsLock(event: KeyboardEvent<HTMLInputElement>) {
    setCapsLock(event.getModifierState("CapsLock"));
  }

  const passwordDescription =
    [errors.password ? "password-error" : null, capsLock ? "caps-lock" : null]
      .filter(Boolean)
      .join(" ") || undefined;

  return (
    <main className="grid flex-1 lg:grid-cols-2">
      <section className="flex flex-col px-6 py-6 sm:px-10">
        <div className="flex items-center gap-2">
          <span className="bg-foreground size-4 rounded-sm" aria-hidden />
          <span className="text-sm font-semibold tracking-tight">
            Fleet Maintenance
          </span>
        </div>

        <div className="flex flex-1 items-center justify-center py-12">
          <div className="w-full max-w-sm">
            <header className="mb-8 space-y-2">
              <h1 className="text-2xl font-semibold tracking-tight">Sign in</h1>
              <p className="text-muted-foreground">
                Vehicles, service records and maintenance state for the fleet.
              </p>
            </header>

            <form
              onSubmit={handleSubmit((values) => login.mutate(values))}
              noValidate
              className="space-y-5"
            >
              <div className="space-y-1.5">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="username"
                  autoFocus
                  placeholder="you@company.com"
                  className="h-10"
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
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    className="h-10 pr-10"
                    aria-invalid={errors.password ? true : undefined}
                    aria-describedby={passwordDescription}
                    onKeyDown={trackCapsLock}
                    onKeyUp={trackCapsLock}
                    {...register("password")}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((shown) => !shown)}
                    aria-label="Show password"
                    aria-pressed={showPassword}
                    aria-controls="password"
                    className="text-muted-foreground hover:text-foreground absolute inset-y-0 right-0 flex w-10 items-center justify-center rounded-r-md transition-colors duration-120 focus-visible:ring-offset-0"
                  >
                    {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                  </button>
                </div>
                {errors.password ? (
                  <p id="password-error" className="text-destructive text-xs">
                    {errors.password.message}
                  </p>
                ) : null}
                {capsLock ? (
                  <p id="caps-lock" className="text-muted-foreground text-xs">
                    Caps Lock is on.
                  </p>
                ) : null}
              </div>

              {/* The server's answer, verbatim: a wrong password and an
                  unreachable API are different problems. Keyed on the attempt,
                  so a second refusal shakes again. */}
              {login.error ? (
                <p
                  key={login.submittedAt}
                  role="alert"
                  className="border-destructive/40 bg-destructive/10 text-destructive animate-[refuse_320ms_ease-in-out] rounded-md border px-3 py-2 text-sm"
                >
                  {login.error.status === 401
                    ? "Those credentials were not accepted."
                    : login.error.message}
                </p>
              ) : null}

              <Button
                type="submit"
                className="h-10 w-full"
                disabled={login.isPending}
              >
                {login.isPending ? (
                  <>
                    <Spinner />
                    Signing in…
                  </>
                ) : (
                  "Sign in"
                )}
              </Button>
            </form>

            <div className="mt-8 space-y-3">
              <p className="text-muted-foreground flex items-center gap-3 text-xs">
                <span className="bg-border h-px flex-1" aria-hidden />
                Or sign in with a demo account
                <span className="bg-border h-px flex-1" aria-hidden />
              </p>
              <div className="grid gap-2 sm:grid-cols-2">
                {DEMO_ACCOUNTS.map((account) => (
                  <button
                    key={account.email}
                    type="button"
                    onClick={() => signInAs(account)}
                    disabled={login.isPending}
                    className="hover:bg-subtle hover:border-foreground/20 rounded-md border px-3 py-2.5 text-left transition-colors duration-120 disabled:pointer-events-none disabled:opacity-50"
                  >
                    <span className="block text-sm font-medium">
                      {account.role}
                    </span>
                    <span className="text-muted-foreground block truncate text-xs">
                      {account.email}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <aside className="hidden p-3 lg:block">
        <ServiceCyclePreview />
      </aside>
    </main>
  );
}

function EyeIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="size-4"
      aria-hidden
    >
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function EyeOffIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="size-4"
      aria-hidden
    >
      <path d="M3 3l18 18" />
      <path d="M10.6 5.1A10.8 10.8 0 0 1 12 5c6.5 0 10 7 10 7a17.6 17.6 0 0 1-3.1 3.9" />
      <path d="M6.6 6.6C3.8 8.4 2 12 2 12s3.5 7 10 7a9.7 9.7 0 0 0 5.4-1.6" />
      <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" />
    </svg>
  );
}

function Spinner() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="size-4 animate-spin" aria-hidden>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity={0.25} strokeWidth={2.5} />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" />
    </svg>
  );
}

"use client";

import { FormEvent, useState } from "react";

import BrandLogo from "./BrandLogo";
import { apiFetch } from "@/lib/api";
import type { Account } from "@/lib/types";


type AuthMode = "login" | "signup";

type AuthResponse = {
  message: string;
  account: Account;
};

type AuthScreenProps = {
  onAuthenticated: (account: Account) => void;
};

export default function AuthScreen({
  onAuthenticated,
}: AuthScreenProps) {
  const [mode, setMode] = useState<AuthMode>("login");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const changeMode = (nextMode: AuthMode) => {
    setMode(nextMode);
    setError("");
    setPassword("");
    setPasswordConfirm("");
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");

    if (mode === "signup" && password !== passwordConfirm) {
      setError("Passwords do not match.");
      return;
    }

    setIsLoading(true);
    try {
      const payload =
        mode === "signup"
          ? {
              full_name: fullName.trim(),
              email: email.trim(),
              password,
              password_confirm: passwordConfirm,
            }
          : {
              email: email.trim(),
              password,
            };

      const response = await apiFetch<AuthResponse>(
        mode === "signup" ? "/auth/signup" : "/auth/login",
        {
          method: "POST",
          body: JSON.stringify(payload),
        },
      );

      onAuthenticated(response.account);
    } catch (authError) {
      setError(
        authError instanceof Error
          ? authError.message
          : "Authentication failed.",
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="relative min-h-screen overflow-hidden bg-slate-950 px-5 py-8 text-white">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-[-10rem] top-[-10rem] h-96 w-96 rounded-full bg-indigo-600/20 blur-3xl" />
        <div className="absolute bottom-[-12rem] right-[-8rem] h-[30rem] w-[30rem] rounded-full bg-violet-600/15 blur-3xl" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.025)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.025)_1px,transparent_1px)] bg-[size:48px_48px]" />
      </div>

      <div className="relative mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl items-center gap-12 lg:grid-cols-[1.05fr_0.95fr]">
        <section className="hidden lg:block">
          <BrandLogo size="lg" showText />
          <h1 className="mt-8 max-w-xl text-5xl font-bold leading-tight tracking-tight">
            Manage people with a conversation, not a control panel.
          </h1>
          <p className="mt-5 max-w-xl text-lg leading-8 text-slate-400">
            UserOps AI turns natural-language instructions into safe, auditable
            user-management actions.
          </p>

          <div className="mt-10 grid max-w-xl gap-4 sm:grid-cols-2">
            {[
              ["Natural commands", "Create, find, update, list, and remove users."],
              ["Safer actions", "Duplicate detection and deletion confirmation built in."],
              ["Secure access", "Separate operator accounts with password-based sign in."],
              ["Fast workflow", "Use a name, email, or user ID without hunting through forms."],
            ].map(([title, description]) => (
              <div
                key={title}
                className="rounded-2xl border border-white/10 bg-white/[0.035] p-5 backdrop-blur"
              >
                <p className="font-semibold text-slate-100">{title}</p>
                <p className="mt-2 text-sm leading-6 text-slate-400">
                  {description}
                </p>
              </div>
            ))}
          </div>
        </section>

        <section className="mx-auto w-full max-w-md">
          <div className="mb-7 flex justify-center lg:hidden">
            <BrandLogo size="lg" showText />
          </div>

          <div className="rounded-[2rem] border border-white/10 bg-slate-900/80 p-6 shadow-2xl shadow-black/30 backdrop-blur-xl sm:p-8">
            <div>
              <p className="text-sm font-semibold text-indigo-300">
                {mode === "login" ? "Welcome back" : "Create your workspace account"}
              </p>
              <h2 className="mt-2 text-3xl font-bold tracking-tight">
                {mode === "login" ? "Sign in to UserOps" : "Get started"}
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-400">
                {mode === "login"
                  ? "Continue securely to your operations workspace."
                  : "Your account is separate from the users you manage."}
              </p>
            </div>

            <div className="mt-6 grid grid-cols-2 rounded-xl bg-slate-950/70 p-1">
              {(["login", "signup"] as const).map((tab) => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => changeMode(tab)}
                  className={`rounded-lg px-3 py-2.5 text-sm font-semibold transition ${
                    mode === tab
                      ? "bg-indigo-500 text-white shadow"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  {tab === "login" ? "Sign in" : "Create account"}
                </button>
              ))}
            </div>

            <form onSubmit={handleSubmit} className="mt-6 space-y-4">
              {mode === "signup" && (
                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-slate-200">
                    Full name
                  </span>
                  <input
                    type="text"
                    autoComplete="name"
                    required
                    minLength={2}
                    value={fullName}
                    onChange={(event) => setFullName(event.target.value)}
                    placeholder="Ayesha Khan"
                    className="auth-input"
                  />
                </label>
              )}

              <label className="block">
                <span className="mb-2 block text-sm font-medium text-slate-200">
                  Email address
                </span>
                <input
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@example.com"
                  className="auth-input"
                />
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-medium text-slate-200">
                  Password
                </span>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    autoComplete={mode === "login" ? "current-password" : "new-password"}
                    required
                    minLength={mode === "signup" ? 8 : 1}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder={mode === "signup" ? "At least 8 characters" : "Your password"}
                    className="auth-input pr-20"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((current) => !current)}
                    className="absolute inset-y-0 right-3 text-xs font-semibold text-indigo-300 hover:text-indigo-200"
                  >
                    {showPassword ? "Hide" : "Show"}
                  </button>
                </div>
              </label>

              {mode === "signup" && (
                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-slate-200">
                    Confirm password
                  </span>
                  <input
                    type={showPassword ? "text" : "password"}
                    autoComplete="new-password"
                    required
                    minLength={8}
                    value={passwordConfirm}
                    onChange={(event) => setPasswordConfirm(event.target.value)}
                    placeholder="Repeat your password"
                    className="auth-input"
                  />
                </label>
              )}

              {error && (
                <div role="alert" className="rounded-xl border border-red-400/20 bg-red-400/10 px-4 py-3 text-sm text-red-200">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={isLoading}
                className="w-full rounded-xl bg-gradient-to-r from-indigo-500 to-violet-600 px-4 py-3.5 font-semibold text-white shadow-lg shadow-indigo-500/15 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isLoading
                  ? mode === "login"
                    ? "Signing in..."
                    : "Creating account..."
                  : mode === "login"
                    ? "Sign in"
                    : "Create account"}
              </button>
            </form>

            <p className="mt-5 text-center text-xs leading-5 text-slate-500">
              Passwords are securely hashed. Your operator account is not mixed
              with the users managed by the chatbot.
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}

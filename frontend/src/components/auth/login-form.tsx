"use client";

import { useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { ArrowRight } from "lucide-react";

import { OAuthBlock, OAuthDivider } from "@/components/auth/oauth-buttons";
import { Button, Input, Label } from "@/components/ui";
import { useAuth } from "@/hooks";
import { apiClient, ApiError } from "@/lib/api-client";
import { ROUTES } from "@/lib/constants";
import { EMAIL_RE } from "@/lib/utils";
import { useAuthStore } from "@/stores";
import type { User } from "@/types";

export function LoginForm() {
  const t = useTranslations("auth");
  const { login } = useAuth();
  const { setUser, setAccessToken } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otpEmail, setOtpEmail] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [otpLoading, setOtpLoading] = useState(false);
  const [otpError, setOtpError] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [emailTouched, setEmailTouched] = useState(false);

  const emailValid = !email || EMAIL_RE.test(email);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      await login({ email, password });
      toast.success(t("loginSuccess"));
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Login failed. Please try again.";
      setError(message);
      toast.error(message);
      setIsLoading(false);
    }
  };

  const handleOtpRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!EMAIL_RE.test(otpEmail)) {
      setOtpError("Please enter a valid email address");
      return;
    }
    setOtpError("");
    setOtpLoading(true);
    try {
      await apiClient.post("/auth/supabase-otp/request", { email: otpEmail });
      setOtpSent(true);
      toast.success("Check your email for a sign-in code");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not send sign-in code";
      setOtpError(message);
      toast.error(message);
    } finally {
      setOtpLoading(false);
    }
  };

  const handleOtpVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setOtpError("");
    setOtpLoading(true);
    try {
      const data = await apiClient.post<{ user: User; access_token: string }>(
        "/auth/supabase-otp/verify",
        { email: otpEmail, token: otpCode.trim() },
      );
      setUser(data.user);
      setAccessToken(data.access_token);
      toast.success(t("loginSuccess"));
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Invalid or expired sign-in code";
      setOtpError(message);
      toast.error(message);
    } finally {
      setOtpLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <span className="eyebrow text-foreground/55">{t("welcomeBack")}</span>
        <h1 className="text-display-md text-foreground [&_em]:font-accent [&_em]:font-normal [&_em]:italic">
          Sign in to <em>your workspace.</em>
        </h1>
        <p className="text-foreground/65 text-sm">
          {t("noAccount")}{" "}
          <Link
            href={ROUTES.REGISTER}
            className="text-foreground hover:text-foreground/80 font-medium underline-offset-4 hover:underline"
          >
            {t("register")}
          </Link>
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="space-y-1.5">
          <Label
            htmlFor="email"
            className="text-foreground/80 text-xs font-medium tracking-wider uppercase"
          >
            {t("email")}
          </Label>
          <Input
            id="email"
            type="email"
            placeholder={t("emailPlaceholder")}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            onBlur={() => setEmailTouched(true)}
            required
            disabled={isLoading}
            autoComplete="email"
            className={`h-12 rounded-xl ${emailTouched && email && !emailValid ? "border-destructive" : ""}`}
          />
          {emailTouched && email && !emailValid && (
            <p className="text-destructive text-xs">{t("emailRequired")}</p>
          )}
        </div>

        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <Label
              htmlFor="password"
              className="text-foreground/80 text-xs font-medium tracking-wider uppercase"
            >
              {t("password")}
            </Label>
            <Link
              href={ROUTES.FORGOT_PASSWORD}
              className="text-foreground/55 hover:text-foreground text-xs font-medium underline-offset-4 hover:underline"
            >
              {t("forgotShort")}
            </Link>
          </div>
          <Input
            id="password"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={isLoading}
            autoComplete="current-password"
            className="h-12 rounded-xl"
          />
        </div>

        {error && (
          <p className="border-destructive/30 bg-destructive/5 text-destructive rounded-lg border px-3 py-2 text-sm">
            {error}
          </p>
        )}

        <Button
          type="submit"
          disabled={isLoading}
          className="bg-foreground text-background hover:bg-foreground/90 h-12 w-full rounded-full text-base font-medium"
        >
          {isLoading ? (
            t("loggingIn")
          ) : (
            <>
              {t("login")}
              <ArrowRight className="ml-2 h-4 w-4" />
            </>
          )}
        </Button>
      </form>

      <OAuthBlock label={t("orSignInWith")} />

      <div className="space-y-4">
        <OAuthDivider label="or email code" />
        <form onSubmit={otpSent ? handleOtpVerify : handleOtpRequest} className="space-y-3">
          <div className="space-y-1.5">
            <Label
              htmlFor="otp-email"
              className="text-foreground/80 text-xs font-medium tracking-wider uppercase"
            >
              {t("email")}
            </Label>
            <Input
              id="otp-email"
              type="email"
              placeholder={t("emailPlaceholder")}
              value={otpEmail}
              onChange={(e) => setOtpEmail(e.target.value)}
              required
              disabled={otpLoading || otpSent}
              autoComplete="email"
              className="h-12 rounded-xl"
            />
          </div>
          {otpSent && (
            <div className="space-y-1.5">
              <Label
                htmlFor="otp-code"
                className="text-foreground/80 text-xs font-medium tracking-wider uppercase"
              >
                Sign-in code
              </Label>
              <Input
                id="otp-code"
                inputMode="numeric"
                autoComplete="one-time-code"
                placeholder="123456"
                value={otpCode}
                onChange={(e) => setOtpCode(e.target.value)}
                required
                disabled={otpLoading}
                className="h-12 rounded-xl"
              />
            </div>
          )}
          {otpError && (
            <p className="border-destructive/30 bg-destructive/5 text-destructive rounded-lg border px-3 py-2 text-sm">
              {otpError}
            </p>
          )}
          <Button
            type="submit"
            disabled={otpLoading}
            variant="outline"
            className="h-12 w-full rounded-full text-base font-medium"
          >
            {otpLoading ? "Working…" : otpSent ? "Verify code" : "Send sign-in code"}
          </Button>
        </form>
      </div>
    </div>
  );
}

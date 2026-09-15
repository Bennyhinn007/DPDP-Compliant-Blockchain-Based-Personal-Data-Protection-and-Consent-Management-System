/**
 * Login Page.
 *
 * Professional healthcare portal authentication.
 */

import { useState, type FormEvent } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { ShieldCheck, Lock, Mail, AlertCircle, KeyRound } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { getErrorMessage } from "@/services/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { GoogleSignInButton } from "@/components/shared/GoogleSignInButton";

export function LoginPage() {
  const { login, loginWithDid } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [didLoading, setDidLoading] = useState(false);

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || "/dashboard";

  const routeByRole = (role: string) => {
    if (role === "admin" || role === "dpo") {
      navigate("/dpo", { replace: true });
    } else {
      navigate(from, { replace: true });
    }
  };

  const handleDidLogin = async () => {
    setError("");
    setDidLoading(true);
    try {
      const user = await loginWithDid();
      routeByRole(user.role);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setDidLoading(false);
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const user = await login(email, password);
      routeByRole(user.role);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-neutral-50 px-4">
      <div className="relative w-full max-w-md">
        {/* Logo header */}
        <div className="mb-8 text-center">
          <img
            src="/logo-256.png"
            alt="DPDP Health logo"
            className="mx-auto mb-4 h-24 w-24 object-contain"
          />
          <h1 className="text-2xl font-bold text-neutral-900">DPDP Healthcare Platform</h1>
          <p className="mt-1 text-sm text-neutral-500">
            Secure, consent-driven health data management
          </p>
        </div>

        {/* Login card */}
        <div className="rounded-xl border border-neutral-200 bg-white p-8 shadow-sm">
          <h2 className="mb-1 text-lg font-semibold text-neutral-800">Sign in</h2>
          <p className="mb-6 text-sm text-neutral-500">
            Access your health data securely
          </p>

          {error && (
            <div className="mb-4 flex items-center gap-2 rounded-md bg-danger/5 px-3 py-2.5 text-sm text-danger">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="pl-10"
                  required
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="pl-10"
                  required
                />
              </div>
            </div>

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Signing in..." : "Sign in"}
            </Button>
          </form>

          {/* Divider */}
          <div className="my-5 flex items-center gap-3">
            <div className="h-px flex-1 bg-neutral-200" />
            <span className="text-xs font-medium text-neutral-400">OR</span>
            <div className="h-px flex-1 bg-neutral-200" />
          </div>

          {/* Google Sign-In */}
          <GoogleSignInButton redirectTo={from} onError={setError} text="signin_with" />

          {/* Passwordless DID Sign-In (SIH 26125), optionally RFID 2FA-gated */}
          <Button
            type="button"
            variant="outline"
            className="mt-3 w-full gap-2"
            onClick={handleDidLogin}
            disabled={didLoading}
          >
            <KeyRound className="h-4 w-4" />
            {didLoading ? "Verifying your key..." : "Sign in with DID (passwordless)"}
          </Button>
          <p className="mt-1.5 text-center text-[11px] text-neutral-400">
            Uses your device&apos;s cryptographic key — no password sent. If RFID
            2FA is enabled, tap your card first.
          </p>

          <div className="mt-6 flex items-center justify-center gap-2 text-xs text-neutral-400">
            <ShieldCheck className="h-3.5 w-3.5 text-success" />
            DPDP Act compliant · Data residency: India
          </div>

          <p className="mt-4 text-center text-sm text-neutral-500">
            Don&apos;t have an account?{" "}
            <Link to="/register" className="font-medium text-primary-600 hover:text-primary-700">
              Register
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

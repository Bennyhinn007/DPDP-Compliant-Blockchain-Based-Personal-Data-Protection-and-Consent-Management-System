/**
 * Registration Page.
 *
 * Professional healthcare portal registration with full validation.
 */

import { useState, type FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { ShieldCheck, User, Mail, Lock, AlertCircle, CheckCircle2 } from "lucide-react";
import { authService } from "@/services/authService";
import { getErrorMessage } from "@/services/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { GoogleSignInButton } from "@/components/shared/GoogleSignInButton";

export function RegisterPage() {
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const validate = (): boolean => {
    const errors: Record<string, string> = {};
    if (!fullName || fullName.trim().length < 2) errors.fullName = "Full name required (min 2 characters)";
    if (!email || !email.includes("@")) errors.email = "Valid email required";
    if (!password || password.length < 8) errors.password = "Password must be at least 8 characters";
    if (password !== confirmPassword) errors.confirmPassword = "Passwords do not match";
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (!validate()) return;

    setLoading(true);
    try {
      await authService.register(email, password, "patient", fullName);
      setSuccess(true);
      setTimeout(() => navigate("/login"), 2000);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-50 px-4">
        <div className="w-full max-w-md rounded-xl border border-neutral-200 bg-white p-8 text-center shadow-sm">
          <CheckCircle2 className="mx-auto h-12 w-12 text-success" />
          <h2 className="mt-4 text-xl font-semibold text-neutral-800">Registration Successful</h2>
          <p className="mt-2 text-sm text-neutral-500">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50 px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="mb-6 text-center">
          <img
            src="/logo-256.png"
            alt="DPDP Health logo"
            className="mx-auto mb-3 h-16 w-16 object-contain"
          />
          <h1 className="text-xl font-bold text-neutral-900">DPDP Healthcare Platform</h1>
          <p className="mt-1 text-sm text-neutral-500">Create your patient account</p>
        </div>

        {/* Form */}
        <div className="rounded-xl border border-neutral-200 bg-white p-8 shadow-sm">
          <h2 className="mb-1 text-lg font-semibold text-neutral-800">Register</h2>
          <p className="mb-5 text-sm text-neutral-500">Your data is protected under the DPDP Act</p>

          {error && (
            <div className="mb-4 flex items-center gap-2 rounded-md bg-danger/5 px-3 py-2.5 text-sm text-danger">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="fullName">Full Name</Label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
                <Input
                  id="fullName"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Rajesh Kumar"
                  className="pl-10"
                />
              </div>
              {fieldErrors.fullName && <p className="text-xs text-danger">{fieldErrors.fullName}</p>}
            </div>

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
                />
              </div>
              {fieldErrors.email && <p className="text-xs text-danger">{fieldErrors.email}</p>}
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
                  placeholder="Min 8 characters"
                  className="pl-10"
                />
              </div>
              {fieldErrors.password && <p className="text-xs text-danger">{fieldErrors.password}</p>}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="confirmPassword">Confirm Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
                <Input
                  id="confirmPassword"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Repeat password"
                  className="pl-10"
                />
              </div>
              {fieldErrors.confirmPassword && <p className="text-xs text-danger">{fieldErrors.confirmPassword}</p>}
            </div>

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Creating account..." : "Create Account"}
            </Button>
          </form>

          {/* Divider */}
          <div className="my-5 flex items-center gap-3">
            <div className="h-px flex-1 bg-neutral-200" />
            <span className="text-xs font-medium text-neutral-400">OR</span>
            <div className="h-px flex-1 bg-neutral-200" />
          </div>

          {/* Google Sign-Up (creates a passwordless patient account) */}
          <GoogleSignInButton redirectTo="/dashboard" onError={setError} text="signup_with" />

          <p className="mt-5 text-center text-sm text-neutral-500">
            Already have an account?{" "}
            <Link to="/login" className="font-medium text-primary-600 hover:text-primary-700">
              Sign in
            </Link>
          </p>

          <div className="mt-4 flex items-center justify-center gap-2 text-xs text-neutral-400">
            <ShieldCheck className="h-3.5 w-3.5 text-success" />
            DPDP Act compliant · Encrypted at rest
          </div>
        </div>
      </div>
    </div>
  );
}

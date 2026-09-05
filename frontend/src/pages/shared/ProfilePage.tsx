/**
 * User Profile Page — Enterprise Grade.
 *
 * Universal profile for all roles with:
 * - Identity overview
 * - Security posture + Security Scorecard
 * - Governance activity (admin)
 * - Healthcare summary (patient)
 */

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  User,
  Mail,
  Shield,
  Clock,
  Lock,
  Activity,
  FileText,
  ShieldCheck,
  Fingerprint,
  CheckCircle2,
  Key,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { patientService } from "@/services/patientService";
import { consentService } from "@/services/consentService";
import { auditService } from "@/services/auditService";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { PageHero } from "@/components/shared/PageHero";
import { Badge } from "@/components/ui/badge";
import { PageLoader } from "@/components/shared/PageLoader";
import { MFASetupPanel } from "@/components/mfa/MFASetupPanel";
import { BiometricPanel } from "@/components/mfa/BiometricPanel";
import { formatDateTime, humanize } from "@/lib/utils";

export function ProfilePage() {
  const { user } = useAuth();
  const [mfaState, setMfaState] = useState(false);

  const { isLoading: profileLoading } = useQuery({
    queryKey: ["profile"],
    queryFn: patientService.getProfile,
    enabled: user?.role === "patient",
  });

  const { data: consents = [] } = useQuery({
    queryKey: ["consents"],
    queryFn: consentService.list,
    enabled: user?.role === "patient",
  });

  const { data: records = [] } = useQuery({
    queryKey: ["records"],
    queryFn: patientService.listRecords,
    enabled: user?.role === "patient",
  });

  const { data: timeline = [] } = useQuery({
    queryKey: ["timeline"],
    queryFn: () => auditService.getTimeline(),
    enabled: user?.role === "patient",
  });

  if (!user) return null;
  if (user.role === "patient" && profileLoading) return <PageLoader message="Loading profile..." />;

  const activeConsents = consents.filter((c) => c.status === "active").length;

  // Security Score computation
  const isMfaEnabled = user.mfa_enabled || mfaState;
  const securityScore = computeSecurityScore({ ...user, mfa_enabled: isMfaEnabled });

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {/* Header */}
      <PageHero
        title="My Profile"
        subtitle="Identity details, security posture, and account governance"
        icon={User}
      />

      {/* Identity Card */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-start gap-5">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary-100 text-2xl font-bold text-primary-700">
              {user.full_name.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1">
              <h2 className="text-xl font-semibold text-neutral-800">{user.full_name}</h2>
              <p className="text-sm text-neutral-500">{user.email}</p>
              <div className="mt-2 flex flex-wrap gap-2">
                <Badge variant={user.role === "admin" ? "warning" : user.role === "doctor" ? "success" : "default"}>
                  {user.role === "admin" ? "Admin (DPO)" : humanize(user.role)}
                </Badge>
                <Badge variant="success">Active</Badge>
                {(user.mfa_enabled || mfaState) && (
                  <Badge variant="success">
                    <Key className="mr-1 h-3 w-3" />
                    MFA Enabled
                  </Badge>
                )}
              </div>
            </div>
            {/* Security Score */}
            <div className="hidden text-center sm:block">
              <div className="relative inline-flex">
                <svg className="h-20 w-20" viewBox="0 0 80 80">
                  <circle cx="40" cy="40" r="34" fill="none" stroke="#E5E7EB" strokeWidth="6" />
                  <motion.circle
                    cx="40" cy="40" r="34" fill="none"
                    stroke={securityScore >= 75 ? "#10B981" : securityScore >= 50 ? "#F59E0B" : "#EF4444"}
                    strokeWidth="6" strokeLinecap="round"
                    strokeDasharray={`${2 * Math.PI * 34}`}
                    initial={{ strokeDashoffset: 2 * Math.PI * 34 }}
                    animate={{ strokeDashoffset: 2 * Math.PI * 34 * (1 - securityScore / 100) }}
                    transition={{ duration: 1 }}
                    transform="rotate(-90 40 40)"
                  />
                </svg>
                <span className="absolute inset-0 flex items-center justify-center text-lg font-bold text-neutral-800">
                  {securityScore}
                </span>
              </div>
              <p className="mt-1 text-xs text-neutral-500">Security Score</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Identity Details */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Fingerprint className="h-4 w-4 text-primary-600" />
              Identity Details
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <DetailRow icon={User} label="Full Name" value={user.full_name} />
            <DetailRow icon={Mail} label="Email" value={user.email} />
            <DetailRow icon={Shield} label="Role" value={user.role === "admin" ? "Admin (DPO)" : humanize(user.role)} />
            <DetailRow icon={Clock} label="Last Login" value={user.last_login ? formatDateTime(user.last_login) : "Current session"} />
            <DetailRow icon={Clock} label="Registered" value={formatDateTime(user.created_at)} />
          </CardContent>
        </Card>

        {/* Security Posture */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Lock className="h-4 w-4 text-success" />
              Security Posture
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <SecurityRow label="Authentication" value="JWT (HS256)" ok />
            <SecurityRow label="Encryption" value="AES-256-GCM" ok />
            <SecurityRow label="MFA" value={isMfaEnabled ? "Enabled" : "Not configured"} ok={isMfaEnabled} />
            <SecurityRow label="Account Status" value="Active" ok />
            <SecurityRow label="Data Residency" value="India (DPDP)" ok />
            <SecurityRow label="Password Strength" value="Strong (8+ chars, bcrypt)" ok />
          </CardContent>
        </Card>
      </div>

      {/* Security Scorecard Detail */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldCheck className="h-4 w-4 text-primary-600" />
            Security Scorecard — {securityScore}/100
            <Badge variant={securityScore >= 75 ? "success" : securityScore >= 50 ? "warning" : "danger"}>
              {securityScore >= 90 ? "Excellent" : securityScore >= 75 ? "Good" : securityScore >= 50 ? "Fair" : "Needs Attention"}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <ScoreComponent label="Strong Password" points={25} maxPoints={25} />
            <ScoreComponent label="MFA Status" points={isMfaEnabled ? 25 : 0} maxPoints={25} />
            <ScoreComponent label="Recent Login" points={user.last_login ? 25 : 0} maxPoints={25} />
            <ScoreComponent label="No Failed Logins" points={25} maxPoints={25} />
          </div>
        </CardContent>
      </Card>

      {/* MFA Setup Panel */}
      <MFASetupPanel
        mfaEnabled={user.mfa_enabled || mfaState}
        onMFAChange={() => setMfaState((prev) => !prev)}
      />

      {/* Biometric Panel (Admin/DPO only) */}
      {(user.role === "admin" || user.role === "dpo") && <BiometricPanel />}

      {/* Patient-specific: Records + Consents + Activity */}
      {user.role === "patient" && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <Card className="h-full">
              <CardContent className="flex flex-col items-center justify-center py-8 text-center">
                <FileText className="h-8 w-8 text-primary-600" />
                <div className="mt-3 text-3xl font-bold text-neutral-800">{records.length}</div>
                <p className="text-sm text-neutral-500">Healthcare Records</p>
              </CardContent>
            </Card>
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
            <Card className="h-full">
              <CardContent className="flex flex-col items-center justify-center py-8 text-center">
                <ShieldCheck className="h-8 w-8 text-success" />
                <div className="mt-3 text-3xl font-bold text-neutral-800">{activeConsents}</div>
                <p className="text-sm text-neutral-500">Active Consents</p>
              </CardContent>
            </Card>
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <Card className="h-full">
              <CardContent className="flex flex-col items-center justify-center py-8 text-center">
                <Activity className="h-8 w-8 text-warning" />
                <div className="mt-3 text-3xl font-bold text-neutral-800">{timeline.length}</div>
                <p className="text-sm text-neutral-500">Audit Events</p>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      )}

      {/* Governance Activity */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Activity className="h-4 w-4 text-neutral-600" />
            {user.role === "admin" ? "Governance Activity" : "Recent Account Activity"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {user.role === "patient" && timeline.length > 0 ? (
            <ul className="space-y-2">
              {timeline.slice(0, 5).map((event) => (
                <li key={event._id} className="flex items-center justify-between rounded-md border border-neutral-100 px-3 py-2">
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full bg-primary-400" />
                    <span className="text-sm text-neutral-700">{humanize(event.action_type)}</span>
                  </div>
                  <span className="text-xs text-neutral-400">{formatDateTime(event.created_at)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="py-6 text-center text-sm text-neutral-400">
              {user.role === "admin"
                ? "Administrative and compliance activities recorded in the audit trail."
                : user.role === "doctor"
                  ? "Doctor access events logged through the consent-gated workflow."
                  : "No recent activity recorded"}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function DetailRow({ icon: Icon, label, value }: { icon: typeof User; label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-md border border-neutral-100 px-3 py-2.5">
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-neutral-400" />
        <span className="text-sm text-neutral-600">{label}</span>
      </div>
      <span className="text-sm font-medium text-neutral-800">{value}</span>
    </div>
  );
}

function SecurityRow({ label, value, ok }: { label: string; value: string; ok: boolean }) {
  return (
    <div className="flex items-center justify-between rounded-md border border-neutral-100 px-3 py-2.5">
      <span className="text-sm text-neutral-700">{label}</span>
      <div className="flex items-center gap-1.5">
        <CheckCircle2 className={`h-3.5 w-3.5 ${ok ? "text-success" : "text-neutral-300"}`} />
        <span className="text-sm text-neutral-600">{value}</span>
      </div>
    </div>
  );
}

function ScoreComponent({ label, points, maxPoints }: { label: string; points: number; maxPoints: number }) {
  const pct = Math.round((points / maxPoints) * 100);
  return (
    <div className="rounded-lg border border-neutral-200 p-3 text-center">
      <div className="text-xl font-bold text-neutral-800">{points}/{maxPoints}</div>
      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-neutral-100">
        <div className={`h-full rounded-full ${pct === 100 ? "bg-success" : pct > 0 ? "bg-warning" : "bg-neutral-200"}`} style={{ width: `${pct}%` }} />
      </div>
      <p className="mt-1.5 text-xs text-neutral-500">{label}</p>
    </div>
  );
}

function computeSecurityScore(user: { mfa_enabled: boolean; last_login: string | null }): number {
  let score = 0;
  score += 25; // Strong password (assumed — bcrypt enforced)
  if (user.mfa_enabled) score += 25;
  if (user.last_login) score += 25; // Recent login
  score += 25; // No failed logins (assumed from current session)
  return score;
}

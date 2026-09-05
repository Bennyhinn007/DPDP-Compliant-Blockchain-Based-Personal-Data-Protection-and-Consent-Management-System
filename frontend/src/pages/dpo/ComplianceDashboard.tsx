/**
 * Compliance Dashboard — Premium Implementation.
 *
 * DPDP compliance score breakdown, rights requests, coverage analysis,
 * and risk indicators. Enterprise-grade compliance operations center.
 */

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Lock,
  ShieldCheck,
  ClipboardList,
  Link2,
  Scale,
  AlertTriangle,
  CheckCircle2,
  FileEdit,
  Trash2,
  TrendingUp,
  Activity,
} from "lucide-react";
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
} from "recharts";
import { complianceService } from "@/services/complianceService";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/shared/StatCard";
import { PageHero } from "@/components/shared/PageHero";
import { ComplianceGauge } from "@/components/shared/ComplianceGauge";
import type { ComplianceScore } from "@/types";

interface CategoryMeta {
  key: keyof ComplianceScore["breakdown"];
  label: string;
  shortLabel: string;
  max: number;
  icon: typeof Lock;
  description: string;
}

const CATEGORIES: CategoryMeta[] = [
  { key: "encryption", label: "Encryption Coverage", shortLabel: "Encryption", max: 20, icon: Lock, description: "AES-256-GCM field-level encryption for all PII" },
  { key: "consent_management", label: "Consent Management", shortLabel: "Consent", max: 25, icon: ShieldCheck, description: "Patient consent lifecycle governance" },
  { key: "audit_logging", label: "Audit Logging", shortLabel: "Audit", max: 20, icon: ClipboardList, description: "Immutable hash-chained audit trail" },
  { key: "blockchain_anchoring", label: "Blockchain Anchoring", shortLabel: "Blockchain", max: 20, icon: Link2, description: "On-chain SHA-256 verification hashes" },
  { key: "dpdp_rights", label: "DPDP Rights", shortLabel: "Rights", max: 15, icon: Scale, description: "Right to access, correction, erasure fulfillment" },
];

export function ComplianceDashboard() {
  const { data: score } = useQuery({
    queryKey: ["compliance-score"],
    queryFn: complianceService.getScore,
  });

  const { data: stats } = useQuery({
    queryKey: ["compliance-stats"],
    queryFn: complianceService.getStats,
  });

  const radarData = score
    ? CATEGORIES.map((c) => ({
        category: c.shortLabel,
        value: Math.round((score.breakdown[c.key] / c.max) * 100),
        fullMark: 100,
      }))
    : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHero
        title="DPDP Compliance Dashboard"
        subtitle="Digital Personal Data Protection Act — Compliance Score & Control Coverage"
        icon={ShieldCheck}
      />

      {/* Top KPI row */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard
          label="DPDP Score"
          value={score ? `${score.overall_score}/100` : "—"}
          icon={TrendingUp}
          variant="success"
          subtitle={score?.grade ? `Grade: ${score.grade}` : undefined}
        />
        <StatCard label="Total Consents" value={stats?.total_consents ?? 0} icon={ShieldCheck} variant="primary" />
        <StatCard label="Blockchain Anchors" value={stats?.total_blockchain_anchors ?? 0} icon={Link2} variant="secondary" />
        <StatCard label="Audit Events" value={stats?.total_audit_events ?? 0} icon={Activity} variant="warning" />
      </div>

      {/* Score section */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Gauge */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Overall Compliance</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-center pb-8 pt-4">
            {score ? (
              <ComplianceGauge score={score.overall_score} grade={score.grade} />
            ) : (
              <div className="h-32 w-32 animate-pulse rounded-full bg-neutral-100" />
            )}
          </CardContent>
        </Card>

        {/* Radar */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Control Coverage Radar</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={240}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="#E5E7EB" />
                <PolarAngleAxis dataKey="category" tick={{ fontSize: 11, fill: "#6B7280" }} />
                <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#9CA3AF" }} />
                <Radar name="Coverage" dataKey="value" stroke="#6366F1" fill="#6366F1" fillOpacity={0.2} />
              </RadarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Breakdown cards */}
      <div>
        <h2 className="mb-3 text-lg font-semibold text-neutral-800">Score Breakdown</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {score &&
            CATEGORIES.map((cat, i) => {
              const value = score.breakdown[cat.key];
              const pct = Math.round((value / cat.max) * 100);
              const Icon = cat.icon;
              const healthy = pct >= 70;
              return (
                <motion.div
                  key={cat.key}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.06 }}
                >
                  <Card className="h-full">
                    <CardContent className="p-4">
                      <div className="flex items-center gap-2">
                        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary-50">
                          <Icon className="h-4 w-4 text-primary-600" />
                        </div>
                        <span className="text-xs font-medium text-neutral-600">{cat.shortLabel}</span>
                      </div>
                      <div className="mt-3 flex items-baseline gap-1">
                        <span className="text-2xl font-bold text-neutral-800">{value}</span>
                        <span className="text-sm text-neutral-400">/ {cat.max}</span>
                      </div>
                      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-neutral-100">
                        <motion.div
                          className={`h-full rounded-full ${healthy ? "bg-success" : "bg-warning"}`}
                          initial={{ width: 0 }}
                          animate={{ width: `${pct}%` }}
                          transition={{ duration: 0.8, delay: i * 0.06 }}
                        />
                      </div>
                      <p className="mt-2 text-[10px] text-neutral-400">{cat.description}</p>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
        </div>
      </div>

      {/* Rights requests + Risk indicators side by side */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Rights Requests */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Scale className="h-4 w-4 text-primary-600" />
              DPDP Rights Requests
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg border border-neutral-200 p-4 text-center">
                <FileEdit className="mx-auto h-5 w-5 text-primary-600" />
                <div className="mt-2 text-2xl font-bold text-neutral-800">{stats?.total_corrections ?? 0}</div>
                <div className="text-xs text-neutral-500">Corrections</div>
                <Badge variant="default" className="mt-1">Section 12</Badge>
              </div>
              <div className="rounded-lg border border-neutral-200 p-4 text-center">
                <Trash2 className="mx-auto h-5 w-5 text-danger" />
                <div className="mt-2 text-2xl font-bold text-neutral-800">{stats?.total_erasures ?? 0}</div>
                <div className="text-xs text-neutral-500">Erasures</div>
                <Badge variant="danger" className="mt-1">Section 12</Badge>
              </div>
            </div>
            <div className="mt-3 rounded-md bg-neutral-50 px-3 py-2 text-xs text-neutral-500">
              {stats?.redacted_records ?? 0} record(s) currently in redacted state
            </div>
          </CardContent>
        </Card>

        {/* Risk indicators */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertTriangle className="h-4 w-4 text-warning" />
              Risk Indicators
            </CardTitle>
          </CardHeader>
          <CardContent>
            {score && (
              <div className="space-y-2">
                {CATEGORIES.filter((c) => score.breakdown[c.key] / c.max < 0.7).length === 0 ? (
                  <div className="flex items-center gap-2 rounded-md bg-success/5 px-3 py-3 text-sm text-success">
                    <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
                    All compliance controls within acceptable thresholds
                  </div>
                ) : (
                  CATEGORIES.filter((c) => score.breakdown[c.key] / c.max < 0.7).map((c) => (
                    <div
                      key={c.key}
                      className="flex items-center gap-2 rounded-md bg-warning/5 px-3 py-2.5 text-sm text-warning"
                    >
                      <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                      <span><strong>{c.shortLabel}</strong> below 70% — review recommended</span>
                    </div>
                  ))
                )}
                <div className="mt-2 rounded-md border border-neutral-100 px-3 py-2.5 text-xs text-neutral-500">
                  Compliance evaluated: {score.evaluated_at ? new Date(score.evaluated_at).toLocaleString() : "—"}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

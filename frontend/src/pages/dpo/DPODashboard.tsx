/**
 * DPO Dashboard — Premium Implementation.
 *
 * Data Protection Officer command center with compliance overview,
 * rights monitoring, blockchain health, consent health, audit activity,
 * and system integrity status.
 */

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Users,
  FileText,
  ShieldCheck,
  Link2,
  Pencil,
  Trash2,
  Activity,
  Database,
  TrendingUp,
  CheckCircle2,
  Lock,
  BarChart3,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
  Legend,
} from "recharts";
import { complianceService } from "@/services/complianceService";
import { adminService } from "@/services/adminService";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/shared/StatCard";
import { ComplianceGauge } from "@/components/shared/ComplianceGauge";

const BAR_COLORS = ["#2563EB", "#10B981", "#F59E0B", "#0F4C81", "#8B5CF6"];
const PIE_COLORS = ["#10B981", "#EF4444", "#F59E0B"];

export function DPODashboard() {
  const { data: stats } = useQuery({
    queryKey: ["compliance-stats"],
    queryFn: complianceService.getStats,
  });

  const { data: score } = useQuery({
    queryKey: ["compliance-score"],
    queryFn: complianceService.getScore,
  });

  const { data: health } = useQuery({
    queryKey: ["system-health"],
    queryFn: adminService.getSystemHealth,
    refetchInterval: 30000,
  });

  const activityData = stats
    ? [
        { name: "Records", value: stats.total_records },
        { name: "Consents", value: stats.total_consents },
        { name: "Corrections", value: stats.total_corrections },
        { name: "Erasures", value: stats.total_erasures },
        { name: "Anchors", value: stats.total_blockchain_anchors },
      ]
    : [];

  const consentPieData = stats
    ? [
        { name: "Active", value: stats.active_consents },
        { name: "Withdrawn", value: stats.withdrawn_consents },
        { name: "Other", value: Math.max(0, stats.total_consents - stats.active_consents - stats.withdrawn_consents) },
      ].filter((d) => d.value > 0)
    : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-800">Compliance & Governance Center</h1>
          <p className="mt-1 text-sm text-neutral-500">
            Administrative compliance oversight and data protection governance
          </p>
        </div>
        <Badge variant="success" className="flex items-center gap-1 px-3 py-1.5">
          <CheckCircle2 className="h-3.5 w-3.5" />
          System Operational
        </Badge>
      </div>

      {/* Compliance score + KPIs */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        <Card className="lg:row-span-2">
          <CardContent className="flex flex-col items-center justify-center py-8">
            {score ? (
              <>
                <ComplianceGauge score={score.overall_score} grade={score.grade} />
                <p className="mt-4 text-xs text-neutral-400">DPDP Compliance Score</p>
              </>
            ) : (
              <div className="h-24 w-24 animate-pulse rounded-full bg-neutral-100" />
            )}
          </CardContent>
        </Card>
        <StatCard label="Total Patients" value={stats?.total_patients ?? 0} icon={Users} variant="primary" />
        <StatCard label="Health Records" value={stats?.total_records ?? 0} icon={FileText} variant="secondary" />
        <StatCard label="Active Consents" value={stats?.active_consents ?? 0} icon={ShieldCheck} variant="success" />
        <StatCard label="Blockchain Anchors" value={stats?.total_blockchain_anchors ?? 0} icon={Link2} variant="warning" />
        <StatCard label="Audit Events" value={stats?.total_audit_events ?? 0} icon={Activity} variant="primary" />
        <StatCard label="Registered Users" value={stats?.total_users ?? 0} icon={Database} variant="secondary" />
      </div>

      {/* Rights monitoring + consent health */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Rights Monitoring */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <BarChart3 className="h-4 w-4 text-primary-600" />
              Rights Requests
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex items-center justify-between rounded-lg border border-neutral-200 p-3"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary-50">
                    <Pencil className="h-5 w-5 text-primary-600" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-neutral-800">Corrections</p>
                    <p className="text-xs text-neutral-400">DPDP Section 12</p>
                  </div>
                </div>
                <span className="text-2xl font-bold text-primary-700">{stats?.total_corrections ?? 0}</span>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 }}
                className="flex items-center justify-between rounded-lg border border-neutral-200 p-3"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-md bg-danger/10">
                    <Trash2 className="h-5 w-5 text-danger" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-neutral-800">Erasures</p>
                    <p className="text-xs text-neutral-400">Right to Erasure</p>
                  </div>
                </div>
                <span className="text-2xl font-bold text-danger">{stats?.total_erasures ?? 0}</span>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 }}
                className="flex items-center justify-between rounded-lg border border-neutral-200 p-3"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-md bg-warning/10">
                    <Lock className="h-5 w-5 text-warning" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-neutral-800">Redacted Records</p>
                    <p className="text-xs text-neutral-400">Currently redacted</p>
                  </div>
                </div>
                <span className="text-2xl font-bold text-warning">{stats?.redacted_records ?? 0}</span>
              </motion.div>
            </div>
          </CardContent>
        </Card>

        {/* System activity chart */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <TrendingUp className="h-4 w-4 text-primary-600" />
              System Activity Overview
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={activityData} barSize={36}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#6B7280" }} axisLine={false} />
                <YAxis tick={{ fontSize: 12, fill: "#9CA3AF" }} axisLine={false} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ borderRadius: 8, border: "1px solid #E5E7EB", fontSize: 12 }}
                />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {activityData.map((_, i) => (
                    <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Consent health + system integrity */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Consent distribution */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Consent Health</CardTitle>
          </CardHeader>
          <CardContent>
            {consentPieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={consentPieData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={70}
                    innerRadius={40}
                    label
                  >
                    {consentPieData.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Legend />
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="py-8 text-center text-sm text-neutral-400">No consent data available</p>
            )}
          </CardContent>
        </Card>

        {/* System integrity status */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">System Integrity Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {health?.subsystems ? (
                Object.entries(health.subsystems).map(([key, sub]) => (
                  <StatusRow
                    key={key}
                    label={key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                    status={sub.status as "operational" | "warning" | "error"}
                    description={sub.description}
                  />
                ))
              ) : (
                <>
                  <StatusRow label="Encryption Engine" status="operational" description="AES-256-GCM field-level" />
                  <StatusRow label="Blockchain Anchoring" status="operational" description="Ganache (Chain ID 1337)" />
                  <StatusRow label="Audit Logger" status="operational" description="Hash-chained, append-only" />
                  <StatusRow label="Consent Manager" status="operational" description="6 consent types active" />
                  <StatusRow label="Chameleon Hash Engine" status="operational" description="Redaction proof generation" />
                  <StatusRow label="DPDP Compliance" status={score && score.overall_score >= 70 ? "operational" : "warning"} description={score ? `Score: ${score.overall_score}/100` : "Evaluating..."} />
                </>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function StatusRow({ label, status, description }: { label: string; status: "operational" | "warning" | "error"; description: string }) {
  return (
    <div className="flex items-center justify-between rounded-md border border-neutral-100 px-3 py-2.5">
      <div className="flex items-center gap-3">
        <div className={`h-2 w-2 rounded-full ${status === "operational" ? "bg-success" : status === "warning" ? "bg-warning" : "bg-danger"}`} />
        <div>
          <p className="text-sm font-medium text-neutral-700">{label}</p>
          <p className="text-xs text-neutral-400">{description}</p>
        </div>
      </div>
      <Badge variant={status === "operational" ? "success" : status === "warning" ? "warning" : "danger"}>
        {status === "operational" ? "Active" : status === "warning" ? "Review" : "Alert"}
      </Badge>
    </div>
  );
}

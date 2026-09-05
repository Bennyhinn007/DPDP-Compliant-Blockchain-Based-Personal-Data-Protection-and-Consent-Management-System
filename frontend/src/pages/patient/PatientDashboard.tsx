/**
 * Patient Dashboard.
 *
 * Overview of privacy score, consents, blockchain anchors, records, and activity.
 */

import { useQuery } from "@tanstack/react-query";
import {
  ShieldCheck,
  FileText,
  Link2,
  Activity,
  TrendingUp,
} from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts";
import { consentService } from "@/services/consentService";
import { patientService } from "@/services/patientService";
import { auditService } from "@/services/auditService";
import { StatCard } from "@/components/shared/StatCard";
import { PageHero } from "@/components/shared/PageHero";
import { DashboardSkeleton } from "@/components/shared/Skeleton";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/contexts/AuthContext";
import { CONSENT_LABELS, statusVariant } from "@/lib/consentMeta";
import { formatDateTime, humanize } from "@/lib/utils";
import type { ConsentType } from "@/types";

const CHART_COLORS = ["#6366F1", "#818CF8", "#4338CA", "#A5B4FC", "#312E81", "#C7D2FE"];

export function PatientDashboard() {
  const { user } = useAuth();

  const { data: consents = [], isLoading: loadingConsents } = useQuery({
    queryKey: ["consents"],
    queryFn: consentService.list,
  });

  const { data: records = [], isLoading: loadingRecords } = useQuery({
    queryKey: ["records"],
    queryFn: patientService.listRecords,
  });

  const { data: timeline = [], isLoading: loadingTimeline } = useQuery({
    queryKey: ["timeline"],
    queryFn: () => auditService.getTimeline(),
  });

  const activeConsents = consents.filter((c) => c.status === "active");
  const blockchainAnchors = records.filter((r) => r.blockchain_tx_ref).length;

  // Privacy score: simple computation from active consents + encryption + records
  const privacyScore = Math.min(
    100,
    Math.round(
      (activeConsents.length > 0 ? 40 : 20) +
        (records.length > 0 ? 30 : 0) +
        (blockchainAnchors > 0 ? 30 : 0)
    )
  );

  // Consent distribution data for chart
  const consentDistribution = activeConsents.reduce((acc, c) => {
    const label = CONSENT_LABELS[c.consent_type as ConsentType] || c.consent_type;
    acc[label] = (acc[label] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const chartData = Object.entries(consentDistribution).map(([name, value]) => ({ name, value }));

  if (loadingConsents && loadingRecords && loadingTimeline) {
    return <DashboardSkeleton />;
  }

  return (
    <div className="space-y-6">
      {/* Hero header */}
      <PageHero
        title={`Welcome back, ${user?.full_name?.split(" ")[0] || "Patient"}`}
        subtitle="Your health data overview and privacy status"
        icon={ShieldCheck}
        pill={{
          label: privacyScore >= 70 ? "Protected" : "Review privacy",
          tone: privacyScore >= 70 ? "success" : "warning",
        }}
      />

      {/* Stat cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Privacy Score"
          value={`${privacyScore}/100`}
          icon={ShieldCheck}
          variant="success"
          subtitle={privacyScore >= 70 ? "Good standing" : "Needs attention"}
        />
        <StatCard
          label="Active Consents"
          value={activeConsents.length}
          icon={TrendingUp}
          variant="primary"
        />
        <StatCard
          label="Blockchain Anchors"
          value={blockchainAnchors}
          icon={Link2}
          variant="secondary"
        />
        <StatCard
          label="Health Records"
          value={records.length}
          icon={FileText}
          variant="warning"
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Recent activity */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary-600" />
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            {timeline.length === 0 ? (
              <p className="py-8 text-center text-sm text-neutral-400">No activity yet</p>
            ) : (
              <ul className="space-y-3">
                {timeline.slice(0, 6).map((event) => (
                  <li key={event._id} className="flex items-start gap-3">
                    <div className="mt-1.5 h-2 w-2 flex-shrink-0 rounded-full bg-primary-500" />
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-neutral-700">
                          {humanize(event.action_type)}
                        </span>
                        <Badge variant={event.severity === "critical" ? "danger" : event.severity === "warning" ? "warning" : "neutral"}>
                          {event.severity}
                        </Badge>
                      </div>
                      <p className="text-xs text-neutral-500">{event.reason}</p>
                      <p className="text-xs text-neutral-400">{formatDateTime(event.created_at)}</p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        {/* Consent distribution chart */}
        <Card>
          <CardHeader>
            <CardTitle>Active Consent Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            {chartData.length === 0 ? (
              <p className="py-8 text-center text-sm text-neutral-400">No active consents</p>
            ) : (
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={chartData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label
                  >
                    {chartData.map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Active consents list */}
      <Card>
        <CardHeader>
          <CardTitle>Your Consents</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {consents.length === 0 ? (
              <p className="col-span-full py-4 text-center text-sm text-neutral-400">
                No consents granted yet
              </p>
            ) : (
              consents.map((c) => (
                <div key={c._id} className="rounded-lg border border-neutral-200 p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-neutral-700">
                      {CONSENT_LABELS[c.consent_type as ConsentType]}
                    </span>
                    <Badge variant={statusVariant(c.status)}>{c.status}</Badge>
                  </div>
                  <p className="mt-1 text-xs text-neutral-400">{c.processing_entity_name}</p>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

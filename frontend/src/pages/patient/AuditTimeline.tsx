/**
 * Audit Timeline.
 *
 * Vertical timeline of audit events with filters, search, and statistics.
 */

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Search,
  LogIn,
  FilePlus,
  FileEdit,
  Trash2,
  ShieldCheck,
  Activity,
  type LucideIcon,
} from "lucide-react";
import { auditService } from "@/services/auditService";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/shared/StatCard";
import { PageHero } from "@/components/shared/PageHero";
import { formatDateTime, humanize } from "@/lib/utils";
import type { AuditEvent } from "@/types";

const ACTION_ICONS: Record<string, LucideIcon> = {
  login: LogIn,
  create: FilePlus,
  update: FileEdit,
  delete: Trash2,
  consent_grant: ShieldCheck,
  consent_withdraw: ShieldCheck,
  consent_modify: ShieldCheck,
};

function iconFor(actionType: string): LucideIcon {
  return ACTION_ICONS[actionType] || Activity;
}

const EVENT_TYPE_OPTIONS = [
  { value: "", label: "All Events" },
  { value: "login", label: "Login" },
  { value: "create", label: "Record Created" },
  { value: "update", label: "Record Updated" },
  { value: "delete", label: "Record Erased" },
  { value: "consent_grant", label: "Consent Granted" },
  { value: "consent_withdraw", label: "Consent Withdrawn" },
];

export function AuditTimeline() {
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");

  const { data: events = [] } = useQuery({
    queryKey: ["timeline", typeFilter],
    queryFn: () => auditService.getTimeline(typeFilter || undefined),
  });

  const filtered = useMemo(() => {
    if (!search) return events;
    const q = search.toLowerCase();
    return events.filter(
      (e) =>
        e.reason?.toLowerCase().includes(q) ||
        e.action_type?.toLowerCase().includes(q) ||
        e.resource_type?.toLowerCase().includes(q)
    );
  }, [events, search]);

  const stats = useMemo(() => {
    const today = new Date().toDateString();
    return {
      total: events.length,
      today: events.filter((e) => new Date(e.created_at).toDateString() === today).length,
      critical: events.filter((e) => e.severity === "critical").length,
    };
  }, [events]);

  return (
    <div className="space-y-6">
      <PageHero
        title="Audit Timeline"
        subtitle="Complete history of actions on your data"
        icon={Activity}
      />

      {/* Statistics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="Total Events" value={stats.total} icon={Activity} variant="primary" />
        <StatCard label="Today" value={stats.today} icon={LogIn} variant="success" />
        <StatCard label="Critical" value={stats.critical} icon={ShieldCheck} variant="warning" />
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="flex flex-col gap-3 p-4 sm:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
            <Input
              placeholder="Search events..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10"
            />
          </div>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="h-10 rounded-md border border-neutral-300 bg-white px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 sm:w-56"
          >
            {EVENT_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </CardContent>
      </Card>

      {/* Timeline */}
      <Card>
        <CardHeader>
          <CardTitle>Activity Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          {filtered.length === 0 ? (
            <p className="py-12 text-center text-sm text-neutral-400">No events match your filters</p>
          ) : (
            <ol className="relative space-y-6 border-l-2 border-neutral-100 pl-6">
              {filtered.map((event) => (
                <TimelineItem key={event._id} event={event} />
              ))}
            </ol>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function TimelineItem({ event }: { event: AuditEvent }) {
  const Icon = iconFor(event.action_type);
  const severityVariant =
    event.severity === "critical" ? "danger" : event.severity === "warning" ? "warning" : "neutral";

  return (
    <li className="relative">
      {/* Dot + icon */}
      <span className="absolute -left-[2.1rem] flex h-7 w-7 items-center justify-center rounded-full border-2 border-white bg-primary-100">
        <Icon className="h-3.5 w-3.5 text-primary-600" />
      </span>

      <div className="rounded-lg border border-neutral-200 p-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-neutral-800">
            {humanize(event.action_type)}
          </span>
          <Badge variant={severityVariant}>{event.severity}</Badge>
        </div>
        <p className="mt-1 text-sm text-neutral-600">{event.reason}</p>
        <div className="mt-2 flex items-center gap-3 text-xs text-neutral-400">
          <span>{humanize(event.actor_role)}</span>
          <span>·</span>
          <span>{humanize(event.resource_type)}</span>
          <span>·</span>
          <span>{formatDateTime(event.created_at)}</span>
        </div>
      </div>
    </li>
  );
}

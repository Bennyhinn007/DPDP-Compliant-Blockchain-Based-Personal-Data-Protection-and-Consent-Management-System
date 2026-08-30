/**
 * DPDP Operations Center — Admin/DPO Operational Hub.
 *
 * Manages correction/erasure requests, chameleon hash proofs,
 * blockchain verification, and compliance reporting.
 * Every button calls a real backend API.
 */

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Pencil, Trash2, Eye, CheckCircle2, Clock,
  FileText, Link2, Download, Activity,
} from "lucide-react";
import { adminService, type ChameleonRequest, type AuditEntry, type BlockchainAnchor } from "@/services/adminService";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { PageLoader } from "@/components/shared/PageLoader";
import { StatCard } from "@/components/shared/StatCard";
import { formatDateTime } from "@/lib/utils";
import { toast } from "sonner";

type DetailView = {
  request: ChameleonRequest;
  anchors: BlockchainAnchor[];
  versions: Record<string, unknown>[];
  audit: AuditEntry[];
} | null;

export function DPDPOperationsCenter() {
  const [activeTab, setActiveTab] = useState<"pending" | "executed">("pending");
  const [detail, setDetail] = useState<DetailView>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["dpdp-operations"],
    queryFn: adminService.getPendingRequests,
  });

  const handleViewDetail = async (requestId: string) => {
    try {
      const result = await adminService.getRequestDetail(requestId);
      setDetail({
        request: result.request,
        anchors: result.blockchain_anchors,
        versions: result.version_history,
        audit: result.audit_trail,
      });
    } catch {
      toast.error("Failed to load request details");
    }
  };

  const handleExportReport = async () => {
    try {
      const report = await adminService.exportComplianceJSON();
      const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `dpdp-compliance-report-${new Date().toISOString().split("T")[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Compliance report exported");
    } catch {
      toast.error("Failed to export report");
    }
  };

  if (isLoading) return <PageLoader message="Loading DPDP Operations..." />;

  const pendingCorrections = data?.pending_corrections ?? [];
  const pendingErasures = data?.pending_erasures ?? [];
  const executedCorrections = data?.executed_corrections ?? [];
  const executedErasures = data?.executed_erasures ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-800">DPDP Operations Center</h1>
          <p className="mt-1 text-sm text-neutral-500">
            Manage data correction and erasure requests — DPDP Section 12 compliance
          </p>
        </div>
        <Button variant="outline" size="sm" className="gap-2" onClick={handleExportReport}>
          <Download className="h-4 w-4" /> Export Report
        </Button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Pending Requests" value={data?.totals?.pending ?? 0} icon={Clock} variant="warning" subtitle="Awaiting action" />
        <StatCard label="Executed" value={data?.totals?.executed ?? 0} icon={CheckCircle2} variant="success" subtitle="Completed" />
        <StatCard label="Corrections" value={pendingCorrections.length + executedCorrections.length} icon={Pencil} variant="primary" subtitle="Total corrections" />
        <StatCard label="Erasures" value={pendingErasures.length + executedErasures.length} icon={Trash2} variant="secondary" subtitle="Total erasures" />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-neutral-200">
        <button onClick={() => setActiveTab("pending")} className={`px-4 py-2 text-sm font-medium ${activeTab === "pending" ? "border-b-2 border-primary-600 text-primary-700" : "text-neutral-500"}`}>
          Pending ({pendingCorrections.length + pendingErasures.length})
        </button>
        <button onClick={() => setActiveTab("executed")} className={`px-4 py-2 text-sm font-medium ${activeTab === "executed" ? "border-b-2 border-primary-600 text-primary-700" : "text-neutral-500"}`}>
          Executed ({executedCorrections.length + executedErasures.length})
        </button>
      </div>

      {/* Request Lists */}
      {activeTab === "pending" && (
        <div className="space-y-4">
          {pendingCorrections.length === 0 && pendingErasures.length === 0 ? (
            <Card><CardContent className="py-12 text-center text-sm text-neutral-400">No pending requests</CardContent></Card>
          ) : (
            <>
              {pendingCorrections.map((req) => (
                <RequestCard key={req._id} request={req} onView={handleViewDetail} type="correction" />
              ))}
              {pendingErasures.map((req) => (
                <RequestCard key={req._id} request={req} onView={handleViewDetail} type="erasure" />
              ))}
            </>
          )}
        </div>
      )}

      {activeTab === "executed" && (
        <div className="space-y-4">
          {executedCorrections.length === 0 && executedErasures.length === 0 ? (
            <Card><CardContent className="py-12 text-center text-sm text-neutral-400">No executed requests</CardContent></Card>
          ) : (
            <>
              {executedCorrections.map((req) => (
                <RequestCard key={req._id} request={req} onView={handleViewDetail} type="correction" />
              ))}
              {executedErasures.map((req) => (
                <RequestCard key={req._id} request={req} onView={handleViewDetail} type="erasure" />
              ))}
            </>
          )}
        </div>
      )}

      {/* Detail Modal */}
      {detail && (
        <Dialog open onClose={() => setDetail(null)} title="Request Details" className="max-w-3xl">
          <div className="space-y-4 max-h-[70vh] overflow-y-auto">
            {/* Request Info */}
            <Card>
              <CardHeader><CardTitle className="text-sm">Request Information</CardTitle></CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-md bg-neutral-50 p-2.5">
                    <p className="text-[10px] font-medium uppercase text-neutral-400">Type</p>
                    <p className="text-sm font-medium capitalize">{detail.request.redaction_type}</p>
                  </div>
                  <div className="rounded-md bg-neutral-50 p-2.5">
                    <p className="text-[10px] font-medium uppercase text-neutral-400">Status</p>
                    <Badge variant={detail.request.status === "executed" ? "success" : detail.request.status === "authorized" ? "warning" : "default"}>{detail.request.status}</Badge>
                  </div>
                  <div className="rounded-md bg-neutral-50 p-2.5">
                    <p className="text-[10px] font-medium uppercase text-neutral-400">Record ID</p>
                    <p className="text-xs font-mono text-neutral-700">{detail.request.resource_id}</p>
                  </div>
                  <div className="rounded-md bg-neutral-50 p-2.5">
                    <p className="text-[10px] font-medium uppercase text-neutral-400">Patient ID</p>
                    <p className="text-xs font-mono text-neutral-700">{detail.request.patient_id}</p>
                  </div>
                  <div className="col-span-2 rounded-md bg-neutral-50 p-2.5">
                    <p className="text-[10px] font-medium uppercase text-neutral-400">Reason</p>
                    <p className="text-sm text-neutral-700">{detail.request.reason}</p>
                  </div>
                  <div className="col-span-2 rounded-md bg-neutral-50 p-2.5">
                    <p className="text-[10px] font-medium uppercase text-neutral-400">Affected Fields</p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {detail.request.affected_fields?.map((f) => (
                        <Badge key={f} variant="default" className="text-[10px]">{f}</Badge>
                      ))}
                    </div>
                  </div>
                  {detail.request.legal_basis && (
                    <div className="col-span-2 rounded-md bg-neutral-50 p-2.5">
                      <p className="text-[10px] font-medium uppercase text-neutral-400">Legal Basis</p>
                      <p className="text-sm text-neutral-700">{detail.request.legal_basis}</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Blockchain Anchors */}
            {detail.anchors.length > 0 && (
              <Card>
                <CardHeader><CardTitle className="flex items-center gap-2 text-sm"><Link2 className="h-4 w-4" />Blockchain Anchors</CardTitle></CardHeader>
                <CardContent className="space-y-2">
                  {detail.anchors.map((a) => (
                    <div key={a._id} className="flex items-center justify-between rounded-md border border-neutral-100 px-3 py-2">
                      <div>
                        <p className="text-xs font-mono text-neutral-700">{a.transaction_hash ? `Tx: ${a.transaction_hash.substring(0, 20)}...` : "No tx hash"}</p>
                        <p className="text-[10px] text-neutral-400">Block #{a.block_number} • {a.transaction_status}</p>
                      </div>
                      <Badge variant={a.transaction_status === "success" ? "success" : "warning"}>{a.transaction_status}</Badge>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            {/* Version History */}
            {detail.versions.length > 0 && (
              <Card>
                <CardHeader><CardTitle className="flex items-center gap-2 text-sm"><FileText className="h-4 w-4" />Version History</CardTitle></CardHeader>
                <CardContent className="space-y-2">
                  {detail.versions.map((v, i) => (
                    <div key={i} className="rounded-md border border-neutral-100 px-3 py-2">
                      <p className="text-xs font-medium text-neutral-700">v{String(v.version ?? i + 1)} — {String(v.modification_type ?? "unknown")}</p>
                      <p className="text-[10px] text-neutral-400">{String(v.reason ?? "")} • {v.created_at ? formatDateTime(v.created_at as string) : ""}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            {/* Audit Trail */}
            {detail.audit.length > 0 && (
              <Card>
                <CardHeader><CardTitle className="flex items-center gap-2 text-sm"><Activity className="h-4 w-4" />Audit Trail</CardTitle></CardHeader>
                <CardContent className="space-y-2">
                  {detail.audit.map((e) => (
                    <div key={e._id} className="flex items-start justify-between rounded-md border border-neutral-100 px-3 py-2">
                      <div>
                        <p className="text-xs font-medium text-neutral-700">{e.action_type} by {e.actor_role}</p>
                        <p className="text-[10px] text-neutral-400">{e.reason}</p>
                      </div>
                      <p className="text-[10px] text-neutral-400">{formatDateTime(e.created_at)}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            <div className="flex justify-end pt-2">
              <Button variant="outline" onClick={() => setDetail(null)}>Close</Button>
            </div>
          </div>
        </Dialog>
      )}
    </div>
  );
}

function RequestCard({ request, onView, type }: { request: ChameleonRequest; onView: (id: string) => void; type: "correction" | "erasure" }) {
  return (
    <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}>
      <Card className="hover:border-primary-200 transition-colors">
        <CardContent className="flex items-center justify-between py-4">
          <div className="flex items-center gap-4">
            <div className={`flex h-10 w-10 items-center justify-center rounded-md ${type === "correction" ? "bg-primary-50" : "bg-danger/10"}`}>
              {type === "correction" ? <Pencil className="h-5 w-5 text-primary-600" /> : <Trash2 className="h-5 w-5 text-danger" />}
            </div>
            <div>
              <p className="text-sm font-medium text-neutral-800 capitalize">{type} Request</p>
              <p className="text-xs text-neutral-500">{request.reason}</p>
              <p className="text-[10px] text-neutral-400 mt-0.5">
                Record: {request.resource_id?.substring(0, 12)}... • {formatDateTime(request.created_at)}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant={request.status === "executed" ? "success" : request.status === "authorized" ? "warning" : "default"}>{request.status}</Badge>
            <Button variant="ghost" size="sm" onClick={() => onView(request._id)}><Eye className="h-4 w-4" /></Button>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

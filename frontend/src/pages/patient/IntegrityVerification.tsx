/**
 * Integrity Verification — Premium Implementation.
 *
 * Blockchain-powered record integrity verification with visual status,
 * network monitoring, transaction details, and verification statistics.
 */

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  Link2,
  Hash,
  Box,
  CheckCircle2,
  XCircle,
  Wifi,
  Copy,
  RefreshCw,
  Lock,
} from "lucide-react";
import { patientService } from "@/services/patientService";
import { integrityService } from "@/services/integrityService";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/shared/StatCard";
import { PageHero } from "@/components/shared/PageHero";
import { TamperDemo } from "@/components/shared/TamperDemo";
import { truncateHash, formatDateTime, humanize } from "@/lib/utils";
import type { VerificationResult } from "@/types";

const STATUS_CONFIG: Record<
  VerificationResult["status"],
  { label: string; variant: "success" | "warning" | "danger" | "neutral"; icon: typeof ShieldCheck; color: string }
> = {
  VERIFIED: { label: "Verified", variant: "success", icon: ShieldCheck, color: "#10B981" },
  VERIFIED_MODIFIED: { label: "Authorized Modification", variant: "warning", icon: ShieldCheck, color: "#F59E0B" },
  VERIFIED_REDACTED: { label: "Lawfully Redacted", variant: "neutral", icon: Lock, color: "#6366F1" },
  INTEGRITY_VIOLATION: { label: "Integrity Violation", variant: "danger", icon: ShieldX, color: "#EF4444" },
  NO_ANCHOR: { label: "No Anchor", variant: "neutral", icon: ShieldAlert, color: "#9CA3AF" },
};

export function IntegrityVerification() {
  const [results, setResults] = useState<Record<string, VerificationResult>>({});
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  const { data: records = [] } = useQuery({
    queryKey: ["records"],
    queryFn: patientService.listRecords,
  });

  const { data: status } = useQuery({
    queryKey: ["blockchain-status"],
    queryFn: integrityService.getStatus,
  });

  const verifyMutation = useMutation({
    mutationFn: (recordId: string) => integrityService.verifyRecord(recordId),
    onSuccess: (result) => {
      setResults((prev) => ({ ...prev, [result.record_id]: result }));
    },
  });

  const verifyAll = () => {
    records.forEach((r) => verifyMutation.mutate(r._id));
  };

  const copyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  // Compute stats from results
  const verified = Object.values(results).filter((r) => r.status === "VERIFIED").length;
  const modified = Object.values(results).filter((r) => r.status === "VERIFIED_MODIFIED").length;
  const redacted = Object.values(results).filter((r) => r.status === "VERIFIED_REDACTED").length;
  const violations = Object.values(results).filter((r) => r.status === "INTEGRITY_VIOLATION").length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHero
        title="Data Integrity Verification"
        subtitle="Verify healthcare records against blockchain-anchored SHA-256 hashes"
        icon={ShieldCheck}
        actions={
          <Button variant="accent" onClick={verifyAll} disabled={records.length === 0 || verifyMutation.isPending}>
            <RefreshCw className={`h-4 w-4 ${verifyMutation.isPending ? "animate-spin" : ""}`} />
            Verify All Records
          </Button>
        }
      />

      {/* Stats row */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="Anchored Records" value={status?.total_anchors ?? 0} icon={Link2} variant="primary" />
        <StatCard label="Verified" value={verified} icon={ShieldCheck} variant="success" />
        <StatCard label="Modified" value={modified + redacted} icon={ShieldAlert} variant="warning" />
        <StatCard label="Violations" value={violations} icon={ShieldX} variant="secondary" />
      </div>

      {/* Live tamper-attempt demo */}
      <TamperDemo />

      {/* Blockchain network status */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <Wifi className={`h-4 w-4 ${status?.connected ? "text-success" : "text-danger"}`} />
                <span className="text-sm font-medium text-neutral-700">
                  {status?.connected ? "Connected" : "Disconnected"}
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm text-neutral-500">
                <span className="font-medium text-neutral-600">Network:</span> Ganache (Local Ethereum)
              </div>
              <div className="flex items-center gap-2 text-sm text-neutral-500">
                <span className="font-medium text-neutral-600">Chain ID:</span> 1337
              </div>
              <div className="flex items-center gap-2 text-sm text-neutral-500">
                <Box className="h-3.5 w-3.5" />
                <span className="font-medium text-neutral-600">Block:</span> #{status?.block_number ?? "—"}
              </div>
            </div>
            <Badge variant={status?.connected ? "success" : "danger"}>
              {status?.connected ? "● Live" : "● Offline"}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Verification results */}
      <div className="space-y-3">
        {records.length === 0 ? (
          <Card>
            <CardContent className="py-16 text-center">
              <ShieldCheck className="mx-auto h-12 w-12 text-neutral-300" />
              <p className="mt-4 text-sm text-neutral-400">No healthcare records to verify</p>
            </CardContent>
          </Card>
        ) : (
          records.map((rec, i) => {
            const result = results[rec._id];
            const config = result ? STATUS_CONFIG[result.status] : null;

            return (
              <motion.div
                key={rec._id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
              >
                <Card className="overflow-hidden">
                  <div className="flex items-stretch">
                    {/* Status color bar */}
                    <div
                      className="w-1.5 flex-shrink-0"
                      style={{ backgroundColor: config?.color ?? "#E5E7EB" }}
                    />
                    <div className="flex-1 p-4">
                      {/* Record header */}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-neutral-100">
                            {config ? (
                              <config.icon className="h-4 w-4" style={{ color: config.color }} />
                            ) : (
                              <Hash className="h-4 w-4 text-neutral-400" />
                            )}
                          </div>
                          <div>
                            <span className="text-sm font-semibold text-neutral-800">{rec.title}</span>
                            <div className="flex items-center gap-2 text-xs text-neutral-400">
                              <Badge variant="neutral">{humanize(rec.record_type)}</Badge>
                              <span>v{rec.version}</span>
                              <span>·</span>
                              <span>{formatDateTime(rec.created_at)}</span>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {config && <Badge variant={config.variant}>{config.label}</Badge>}
                          {!result && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => verifyMutation.mutate(rec._id)}
                              disabled={verifyMutation.isPending}
                            >
                              Verify
                            </Button>
                          )}
                        </div>
                      </div>

                      {/* Verification details */}
                      {result && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: "auto" }}
                          className="mt-4 border-t border-neutral-100 pt-4"
                        >
                          <p className="mb-3 text-sm text-neutral-600">{result.message}</p>
                          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
                            <HashCell
                              label="Current Hash"
                              value={result.current_hash}
                              onCopy={copyHash}
                              copied={copiedHash === result.current_hash}
                            />
                            <HashCell
                              label="Blockchain Hash"
                              value={result.blockchain_hash}
                              onCopy={copyHash}
                              copied={copiedHash === result.blockchain_hash}
                            />
                            <HashCell
                              label="Transaction"
                              value={result.transaction_hash}
                              onCopy={copyHash}
                              copied={copiedHash === result.transaction_hash}
                            />
                            <div className="rounded-md bg-neutral-50 p-2.5">
                              <span className="text-[10px] font-medium uppercase tracking-wide text-neutral-400">
                                Block Number
                              </span>
                              <p className="mt-1 font-mono text-sm font-semibold text-neutral-800">
                                #{result.block_number ?? "—"}
                              </p>
                            </div>
                          </div>

                          {/* Hash match indicator */}
                          <div className="mt-3 flex items-center gap-2 rounded-md border border-neutral-100 px-3 py-2">
                            {result.current_hash === result.blockchain_hash ? (
                              <>
                                <CheckCircle2 className="h-4 w-4 text-success" />
                                <span className="text-xs font-medium text-success">
                                  Hashes match — record integrity confirmed
                                </span>
                              </>
                            ) : result.status.startsWith("VERIFIED") ? (
                              <>
                                <CheckCircle2 className="h-4 w-4 text-primary-600" />
                                <span className="text-xs font-medium text-primary-600">
                                  Authorized modification — chameleon hash proof valid
                                </span>
                              </>
                            ) : (
                              <>
                                <XCircle className="h-4 w-4 text-danger" />
                                <span className="text-xs font-medium text-danger">
                                  Hash mismatch — possible unauthorized modification
                                </span>
                              </>
                            )}
                          </div>
                        </motion.div>
                      )}
                    </div>
                  </div>
                </Card>
              </motion.div>
            );
          })
        )}
      </div>
    </div>
  );
}

function HashCell({
  label,
  value,
  onCopy,
  copied,
}: {
  label: string;
  value: string | undefined;
  onCopy: (v: string) => void;
  copied: boolean;
}) {
  return (
    <div className="group rounded-md bg-neutral-50 p-2.5">
      <span className="text-[10px] font-medium uppercase tracking-wide text-neutral-400">{label}</span>
      <div className="mt-1 flex items-center gap-1">
        <p className="font-mono text-xs text-neutral-700" title={value}>
          {truncateHash(value, 6)}
        </p>
        {value && (
          <button
            onClick={() => onCopy(value)}
            className="ml-auto rounded p-0.5 text-neutral-300 opacity-0 transition-opacity hover:text-neutral-500 group-hover:opacity-100"
            aria-label="Copy hash"
          >
            {copied ? <CheckCircle2 className="h-3 w-3 text-success" /> : <Copy className="h-3 w-3" />}
          </button>
        )}
      </div>
    </div>
  );
}

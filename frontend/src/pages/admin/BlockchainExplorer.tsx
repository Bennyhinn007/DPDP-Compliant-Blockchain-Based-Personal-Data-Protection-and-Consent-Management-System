/**
 * Blockchain Explorer — Admin Tool.
 *
 * Browse, search, and inspect all blockchain anchors.
 * Every row is clickable with full detail views.
 */

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Link2, Search, Eye, Box, CheckCircle2, XCircle, RefreshCw,
} from "lucide-react";
import { adminService, type BlockchainAnchor } from "@/services/adminService";
import { assetService } from "@/services/assetService";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { PageLoader } from "@/components/shared/PageLoader";
import { PageHero } from "@/components/shared/PageHero";
import { formatDateTime } from "@/lib/utils";
import { toast } from "sonner";

export function BlockchainExplorer() {
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [page, setPage] = useState(0);
  const [selectedAnchor, setSelectedAnchor] = useState<{ anchor: BlockchainAnchor; record: Record<string, unknown> | null } | null>(null);
  const pageSize = 20;

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["blockchain-explorer", search, page],
    queryFn: () => adminService.getBlockchainAnchors(search, page * pageSize, pageSize),
  });

  // SIH 26125: cached smart-contract events (identity/role/NFT). Additive.
  const { data: chainEvents = [] } = useQuery({
    queryKey: ["chain-events"],
    queryFn: () => assetService.chainEvents(50),
  });

  const handleSearch = () => {
    setSearch(searchInput);
    setPage(0);
  };

  const handleViewAnchor = async (anchorId: string) => {
    try {
      const result = await adminService.getAnchorDetail(anchorId);
      setSelectedAnchor(result);
    } catch {
      toast.error("Failed to load anchor details");
    }
  };

  if (isLoading && !data) return <PageLoader message="Loading Blockchain Explorer..." />;

  const anchors = data?.anchors ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHero
        title="Blockchain Explorer"
        subtitle={`Browse and verify all blockchain anchors — ${total} total anchors`}
        icon={Link2}
        actions={
          <Button variant="outline" size="sm" className="gap-2" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4" /> Refresh
          </Button>
        }
      />

      {/* SIH smart-contract events (identity / role / NFT) — additive */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Box className="h-4 w-4 text-primary-600" />
            Smart-Contract Events (SIH Identity / Roles / NFT)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {chainEvents.length === 0 ? (
            <p className="py-4 text-center text-sm text-neutral-400">
              No contract events yet (identity/role/NFT actions appear here once performed).
            </p>
          ) : (
            <ul className="space-y-2">
              {chainEvents.map((ev) => (
                <li key={ev._id} className="flex items-center justify-between rounded-md border border-neutral-200 px-3 py-2 text-sm">
                  <span className="flex items-center gap-2">
                    <Badge variant="secondary">{ev.contract}</Badge>
                    <span className="font-medium text-neutral-700">{ev.event_name}</span>
                  </span>
                  <span className="flex items-center gap-3 text-xs text-neutral-400">
                    {ev.tx_hash && <code>{ev.tx_hash.slice(0, 14)}…</code>}
                    <span>{formatDateTime(ev.indexed_at)}</span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {/* Search */}
      <Card>
        <CardContent className="flex gap-3 py-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
            <Input
              placeholder="Search by record ID, transaction hash, or data hash..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              className="pl-10"
            />
          </div>
          <Button onClick={handleSearch}>Search</Button>
        </CardContent>
      </Card>

      {/* Anchors Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Link2 className="h-4 w-4 text-primary-600" />
            Blockchain Anchors
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-200 text-left">
                  <th className="pb-3 pr-4 font-medium text-neutral-500">Record</th>
                  <th className="pb-3 pr-4 font-medium text-neutral-500">Tx Hash</th>
                  <th className="pb-3 pr-4 font-medium text-neutral-500">Block</th>
                  <th className="pb-3 pr-4 font-medium text-neutral-500">Status</th>
                  <th className="pb-3 pr-4 font-medium text-neutral-500">Type</th>
                  <th className="pb-3 pr-4 font-medium text-neutral-500">Created</th>
                  <th className="pb-3 font-medium text-neutral-500">Action</th>
                </tr>
              </thead>
              <tbody>
                {anchors.map((anchor, i) => (
                  <motion.tr
                    key={anchor._id}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.02 }}
                    className="border-b border-neutral-100 hover:bg-neutral-50 cursor-pointer"
                    onClick={() => handleViewAnchor(anchor._id)}
                  >
                    <td className="py-3 pr-4">
                      <span className="font-mono text-xs text-neutral-700">{anchor.resource_id?.substring(0, 12)}...</span>
                    </td>
                    <td className="py-3 pr-4">
                      <span className="font-mono text-xs text-neutral-600">
                        {anchor.transaction_hash ? `${anchor.transaction_hash.substring(0, 14)}...` : "—"}
                      </span>
                    </td>
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-1">
                        <Box className="h-3 w-3 text-neutral-400" />
                        <span className="text-xs text-neutral-600">{anchor.block_number ?? "—"}</span>
                      </div>
                    </td>
                    <td className="py-3 pr-4">
                      <Badge variant={anchor.transaction_status === "success" ? "success" : "warning"}>
                        {anchor.transaction_status === "success" ? <CheckCircle2 className="mr-1 h-3 w-3" /> : <XCircle className="mr-1 h-3 w-3" />}
                        {anchor.transaction_status}
                      </Badge>
                    </td>
                    <td className="py-3 pr-4">
                      <span className="text-xs text-neutral-600">{anchor.anchor_type}</span>
                    </td>
                    <td className="py-3 pr-4 text-xs text-neutral-500">{formatDateTime(anchor.created_at)}</td>
                    <td className="py-3">
                      <Button variant="ghost" size="sm"><Eye className="h-4 w-4" /></Button>
                    </td>
                  </motion.tr>
                ))}
                {anchors.length === 0 && (
                  <tr><td colSpan={7} className="py-12 text-center text-neutral-400">No anchors found</td></tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-between">
              <p className="text-xs text-neutral-400">
                Showing {page * pageSize + 1}-{Math.min((page + 1) * pageSize, total)} of {total}
              </p>
              <div className="flex gap-1">
                <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage(page - 1)}>Prev</Button>
                <Button variant="outline" size="sm" disabled={page >= totalPages - 1} onClick={() => setPage(page + 1)}>Next</Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Anchor Detail Modal */}
      {selectedAnchor && (
        <Dialog open onClose={() => setSelectedAnchor(null)} title="Anchor Details" className="max-w-2xl">
          <div className="space-y-4 max-h-[70vh] overflow-y-auto">
            <div className="grid grid-cols-2 gap-3">
              <DetailField label="Anchor ID" value={selectedAnchor.anchor._id} mono />
              <DetailField label="Resource ID" value={selectedAnchor.anchor.resource_id} mono />
              <DetailField label="Transaction Hash" value={selectedAnchor.anchor.transaction_hash || "N/A"} mono />
              <DetailField label="Block Number" value={String(selectedAnchor.anchor.block_number ?? "N/A")} />
              <DetailField label="Status" value={selectedAnchor.anchor.transaction_status} />
              <DetailField label="Anchor Type" value={selectedAnchor.anchor.anchor_type} />
              <DetailField label="Patient ID" value={selectedAnchor.anchor.patient_id} mono />
              <DetailField label="Created" value={formatDateTime(selectedAnchor.anchor.created_at)} />
              <div className="col-span-2">
                <DetailField label="Data Hash (SHA-256)" value={selectedAnchor.anchor.data_hash} mono />
              </div>
            </div>

            {selectedAnchor.record && (
              <Card>
                <CardHeader><CardTitle className="text-sm">Associated Record</CardTitle></CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-3">
                    <DetailField label="Title" value={String(selectedAnchor.record.title ?? "—")} />
                    <DetailField label="Type" value={String(selectedAnchor.record.record_type ?? "—")} />
                    <DetailField label="Version" value={String(selectedAnchor.record.version ?? "1")} />
                    <DetailField label="Redacted" value={selectedAnchor.record.redacted ? "Yes" : "No"} />
                  </div>
                </CardContent>
              </Card>
            )}

            <div className="flex justify-end pt-2">
              <Button variant="outline" onClick={() => setSelectedAnchor(null)}>Close</Button>
            </div>
          </div>
        </Dialog>
      )}
    </div>
  );
}

function DetailField({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="rounded-md bg-neutral-50 p-2.5">
      <p className="text-[10px] font-medium uppercase tracking-wide text-neutral-400">{label}</p>
      <p className={`mt-0.5 text-sm font-medium text-neutral-800 break-all ${mono ? "font-mono text-xs" : ""}`}>{value}</p>
    </div>
  );
}

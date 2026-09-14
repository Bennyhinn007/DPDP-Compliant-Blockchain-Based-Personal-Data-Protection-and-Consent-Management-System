/**
 * Access Control Center — SIH 26125 Phase 3 (ADDITIVE).
 *
 * Shows the SIH permission matrix and lets an admin grant/revoke SIH roles
 * (ADMIN/MANAGER/AUDITOR/USER) to a DID. Dual-enforced: the backend checks
 * healthcare-admin RBAC AND the on-chain PlatformAccessControl.
 *
 * Existing healthcare roles/permissions are unaffected — this is an additional
 * blockchain-role layer.
 */

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ShieldCheck, Check, X, KeyRound, AlertTriangle } from "lucide-react";
import { PageHero } from "@/components/shared/PageHero";
import { PageLoader } from "@/components/shared/PageLoader";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { rolesService } from "@/services/assetService";
import { getErrorMessage } from "@/services/api";

export function AccessControlCenter() {
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [did, setDid] = useState("");
  const [role, setRole] = useState("manager");
  const [busy, setBusy] = useState(false);

  const { data: matrix, isLoading } = useQuery({ queryKey: ["role-matrix"], queryFn: rolesService.matrix });

  const act = async (kind: "grant" | "revoke") => {
    setError("");
    setMsg("");
    setBusy(true);
    try {
      if (kind === "grant") await rolesService.grant(did, role);
      else await rolesService.revoke(did, role);
      setMsg(`Role ${role} ${kind === "grant" ? "granted to" : "revoked from"} ${did}.`);
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  if (isLoading) return <PageLoader message="Loading access control..." />;

  const roles = matrix?.roles ?? ["admin", "manager", "auditor", "user"];
  const rows = matrix ? Object.entries(matrix.matrix) : [];

  return (
    <div className="space-y-6">
      <PageHero
        title="Access Control Center"
        subtitle="Blockchain-enforced SIH roles alongside existing healthcare RBAC"
        icon={ShieldCheck}
        pill={matrix ? { label: matrix.chain_available ? "On-chain live" : "Chain offline", tone: matrix.chain_available ? "success" : "warning" } : undefined}
      />

      <div className="flex items-start gap-2 rounded-lg border border-primary-100 bg-primary-50 px-4 py-3 text-sm text-primary-700">
        <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
        <span>
          SIH roles (ADMIN/MANAGER/AUDITOR/USER) are an <b>additional</b> on-chain layer.
          Existing healthcare roles (patient/doctor/pharmacy/DPO/admin) are unchanged.
          Role changes are dual-enforced and fail closed if the chain is unavailable.
        </span>
      </div>

      {error && <div className="rounded-md bg-danger/5 px-4 py-2.5 text-sm text-danger">{error}</div>}
      {msg && <div className="rounded-md bg-success/10 px-4 py-2.5 text-sm text-success">{msg}</div>}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Grant / revoke */}
        <Card className="lg:col-span-1">
          <CardHeader><CardTitle className="flex items-center gap-2"><KeyRound className="h-5 w-5 text-primary-600" />Assign SIH Role</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1.5"><Label htmlFor="rdid">DID</Label>
              <Input id="rdid" value={did} onChange={(e) => setDid(e.target.value)} placeholder="did:rakshaid:..." /></div>
            <div className="space-y-1.5"><Label htmlFor="rrole">Role</Label>
              <select id="rrole" className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm" value={role} onChange={(e) => setRole(e.target.value)}>
                {roles.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div className="flex gap-2">
              <Button onClick={() => act("grant")} disabled={busy || !did}>Grant</Button>
              <Button variant="outline" onClick={() => act("revoke")} disabled={busy || !did}>Revoke</Button>
            </div>
          </CardContent>
        </Card>

        {/* Permission matrix */}
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>SIH Permission Matrix</CardTitle></CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-neutral-200 text-left">
                    <th className="py-2 pr-3 font-medium text-neutral-500">Operation</th>
                    {roles.map((r) => <th key={r} className="px-2 py-2 text-center font-medium text-primary-700">{r}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {rows.map(([op, perms]) => (
                    <tr key={op} className="border-b border-neutral-100">
                      <td className="py-2 pr-3 text-neutral-700">{op.replace(/_/g, " ")}</td>
                      {roles.map((r) => (
                        <td key={r} className="px-2 py-2 text-center">
                          {perms[r]
                            ? <Check className="mx-auto h-4 w-4 text-success" />
                            : <X className="mx-auto h-4 w-4 text-neutral-300" />}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-3">
              <Badge variant={matrix?.chain_available ? "success" : "warning"}>
                {matrix?.chain_available ? "Blockchain online" : "Blockchain offline (reads cached)"}
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

/**
 * Identity & Access Governance Center — FULL OPERATIONAL VERSION.
 *
 * Complete user lifecycle management with real backend operations:
 * - Search, Sort, Filter, Paginate users
 * - View, Lock, Unlock, Suspend, Activate, Reset MFA, Delete
 * - View audit history, consent history, patient records per user
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Users, UserCheck, UserX, Lock, Unlock, Stethoscope, Search, Shield,
  Heart, AlertTriangle, Clock, Trash2, KeyRound, Eye, ChevronDown,
  RefreshCw, Ban, CheckCircle2,
} from "lucide-react";
import { adminService, type GovernanceUser } from "@/services/adminService";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { StatCard } from "@/components/shared/StatCard";
import { PageLoader } from "@/components/shared/PageLoader";
import { formatDateTime } from "@/lib/utils";
import { toast } from "sonner";

type SortField = "full_name" | "role" | "status" | "last_login" | "risk_level" | "created_at";
type SortDir = "asc" | "desc";
type ActionModal = "lock" | "suspend" | "delete" | "resetMfa" | null;

export function IdentityGovernance() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [riskFilter, setRiskFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sortField, setSortField] = useState<SortField>("created_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [selectedUser, setSelectedUser] = useState<GovernanceUser | null>(null);
  const [detailTab, setDetailTab] = useState<"overview" | "audit" | "consents" | "records">("overview");
  const [actionModal, setActionModal] = useState<ActionModal>(null);
  const [actionReason, setActionReason] = useState("");
  const [page, setPage] = useState(0);
  const pageSize = 15;

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["governance"],
    queryFn: adminService.getGovernanceData,
  });

  // User detail query (only when user selected)
  const { data: userDetail } = useQuery({
    queryKey: ["user-detail", selectedUser?.id],
    queryFn: () => adminService.getUserDetail(selectedUser!.id),
    enabled: !!selectedUser,
  });

  // Mutations
  const unlockMutation = useMutation({
    mutationFn: (userId: string) => adminService.unlockUser(userId),
    onSuccess: () => { toast.success("Account unlocked"); refetch(); queryClient.invalidateQueries({ queryKey: ["user-detail"] }); },
    onError: () => toast.error("Failed to unlock account"),
  });

  const lockMutation = useMutation({
    mutationFn: ({ userId, reason }: { userId: string; reason: string }) =>
      adminService.lockUser(userId, reason),
    onSuccess: () => { toast.success("Account locked"); refetch(); setActionModal(null); setActionReason(""); },
    onError: () => toast.error("Failed to lock account"),
  });

  const suspendMutation = useMutation({
    mutationFn: ({ userId, reason }: { userId: string; reason: string }) =>
      adminService.suspendUser(userId, reason),
    onSuccess: () => { toast.success("Account suspended"); refetch(); setActionModal(null); setActionReason(""); },
    onError: () => toast.error("Failed to suspend account"),
  });

  const activateMutation = useMutation({
    mutationFn: (userId: string) => adminService.activateUser(userId),
    onSuccess: () => { toast.success("Account activated"); refetch(); },
    onError: () => toast.error("Failed to activate account"),
  });

  const resetMfaMutation = useMutation({
    mutationFn: (userId: string) => adminService.resetMFA(userId),
    onSuccess: () => { toast.success("MFA reset"); refetch(); setActionModal(null); },
    onError: () => toast.error("Failed to reset MFA"),
  });

  const deleteMutation = useMutation({
    mutationFn: ({ userId, reason }: { userId: string; reason: string }) =>
      adminService.deleteUser(userId, reason),
    onSuccess: () => { toast.success("User deleted"); refetch(); setSelectedUser(null); setActionModal(null); setActionReason(""); },
    onError: () => toast.error("Failed to delete user"),
  });

  if (isLoading) return <PageLoader message="Loading Identity Governance..." />;

  const metrics = data?.metrics;
  const users = data?.users ?? [];

  // Filter + Sort
  const filtered = users
    .filter((u) => {
      const matchSearch = !search || u.full_name.toLowerCase().includes(search.toLowerCase()) || u.email.toLowerCase().includes(search.toLowerCase());
      const matchRole = !roleFilter || u.role === roleFilter;
      const matchRisk = !riskFilter || u.risk_level === riskFilter;
      const matchStatus = !statusFilter || u.status === statusFilter;
      return matchSearch && matchRole && matchRisk && matchStatus;
    })
    .sort((a, b) => {
      const av = a[sortField] ?? "";
      const bv = b[sortField] ?? "";
      const cmp = String(av).localeCompare(String(bv));
      return sortDir === "asc" ? cmp : -cmp;
    });

  const totalPages = Math.ceil(filtered.length / pageSize);
  const paged = filtered.slice(page * pageSize, (page + 1) * pageSize);

  const handleSort = (field: SortField) => {
    if (sortField === field) setSortDir(sortDir === "asc" ? "desc" : "asc");
    else { setSortField(field); setSortDir("asc"); }
  };

  const SortIcon = ({ field }: { field: SortField }) => (
    sortField === field ? <ChevronDown className={`inline h-3 w-3 ${sortDir === "asc" ? "rotate-180" : ""}`} /> : null
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-800">User Management Center</h1>
          <p className="mt-1 text-sm text-neutral-500">
            Full lifecycle management — lock, unlock, suspend, activate, delete users
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()} className="gap-2">
          <RefreshCw className="h-4 w-4" /> Refresh
        </Button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
        <StatCard label="Total Users" value={metrics?.total_users ?? 0} icon={Users} variant="primary" subtitle="All identities" />
        <StatCard label="Active Today" value={metrics?.active_today ?? 0} icon={UserCheck} variant="success" subtitle="Logged in (24h)" />
        <StatCard label="Patients" value={metrics?.patients ?? 0} icon={Heart} variant="primary" subtitle="Data principals" />
        <StatCard label="Doctors" value={metrics?.doctors ?? 0} icon={Stethoscope} variant="secondary" subtitle="Providers" />
        <StatCard label="Dormant" value={metrics?.dormant ?? 0} icon={UserX} variant="warning" subtitle=">30 days inactive" />
        <StatCard label="Locked" value={metrics?.locked ?? 0} icon={Lock} variant="warning" subtitle="Account lockouts" />
      </div>

      {/* User Directory */}
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="text-base">User Directory ({filtered.length})</CardTitle>
            <div className="flex flex-wrap gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
                <Input placeholder="Search..." value={search} onChange={(e) => { setSearch(e.target.value); setPage(0); }} className="w-44 pl-10" />
              </div>
              <select value={roleFilter} onChange={(e) => { setRoleFilter(e.target.value); setPage(0); }} className="h-10 rounded-md border border-neutral-300 bg-white px-3 text-sm">
                <option value="">All Roles</option>
                <option value="patient">Patient</option>
                <option value="doctor">Doctor</option>
                <option value="admin">Admin</option>
              </select>
              <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }} className="h-10 rounded-md border border-neutral-300 bg-white px-3 text-sm">
                <option value="">All Status</option>
                <option value="active">Active</option>
                <option value="locked">Locked</option>
                <option value="suspended">Suspended</option>
              </select>
              <select value={riskFilter} onChange={(e) => { setRiskFilter(e.target.value); setPage(0); }} className="h-10 rounded-md border border-neutral-300 bg-white px-3 text-sm">
                <option value="">All Risk</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-200 text-left">
                  <th className="cursor-pointer pb-3 pr-4 font-medium text-neutral-500" onClick={() => handleSort("full_name")}>User <SortIcon field="full_name" /></th>
                  <th className="cursor-pointer pb-3 pr-4 font-medium text-neutral-500" onClick={() => handleSort("role")}>Role <SortIcon field="role" /></th>
                  <th className="cursor-pointer pb-3 pr-4 font-medium text-neutral-500" onClick={() => handleSort("status")}>Status <SortIcon field="status" /></th>
                  <th className="cursor-pointer pb-3 pr-4 font-medium text-neutral-500" onClick={() => handleSort("last_login")}>Last Login <SortIcon field="last_login" /></th>
                  <th className="pb-3 pr-4 font-medium text-neutral-500">Records</th>
                  <th className="cursor-pointer pb-3 pr-4 font-medium text-neutral-500" onClick={() => handleSort("risk_level")}>Risk <SortIcon field="risk_level" /></th>
                  <th className="pb-3 font-medium text-neutral-500">Actions</th>
                </tr>
              </thead>
              <tbody>
                {paged.map((user, i) => (
                  <motion.tr key={user.id} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.02 }} className="border-b border-neutral-100 hover:bg-neutral-50">
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-2.5">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-50 text-xs font-bold text-primary-700">{user.full_name.charAt(0).toUpperCase()}</div>
                        <div>
                          <p className="font-medium text-neutral-800">{user.full_name}</p>
                          <p className="text-xs text-neutral-400">{user.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 pr-4"><Badge variant={user.role === "admin" ? "warning" : user.role === "doctor" ? "success" : "default"}>{user.role}</Badge></td>
                    <td className="py-3 pr-4"><Badge variant={user.status === "active" ? "success" : user.status === "locked" ? "danger" : "warning"}>{user.status}</Badge></td>
                    <td className="py-3 pr-4 text-neutral-500">{user.last_login ? formatDateTime(user.last_login) : <span className="text-neutral-300">Never</span>}</td>
                    <td className="py-3 pr-4 text-neutral-600">{user.records_count}</td>
                    <td className="py-3 pr-4"><Badge variant={user.risk_level === "low" ? "success" : user.risk_level === "medium" ? "warning" : "danger"}>{user.risk_level}</Badge></td>
                    <td className="py-3">
                      <div className="flex items-center gap-1">
                        <Button variant="ghost" size="sm" onClick={() => { setSelectedUser(user); setDetailTab("overview"); }} title="View Details"><Eye className="h-4 w-4" /></Button>
                        {user.status === "locked" && <Button variant="ghost" size="sm" onClick={() => unlockMutation.mutate(user.id)} title="Unlock"><Unlock className="h-4 w-4 text-success" /></Button>}
                        {user.status === "active" && <Button variant="ghost" size="sm" onClick={() => { setSelectedUser(user); setActionModal("lock"); }} title="Lock"><Lock className="h-4 w-4 text-warning" /></Button>}
                        {user.status === "suspended" && <Button variant="ghost" size="sm" onClick={() => activateMutation.mutate(user.id)} title="Activate"><CheckCircle2 className="h-4 w-4 text-success" /></Button>}
                        {user.status === "active" && <Button variant="ghost" size="sm" onClick={() => { setSelectedUser(user); setActionModal("suspend"); }} title="Suspend"><Ban className="h-4 w-4 text-danger" /></Button>}
                      </div>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-between">
              <p className="text-xs text-neutral-400">Showing {page * pageSize + 1}-{Math.min((page + 1) * pageSize, filtered.length)} of {filtered.length}</p>
              <div className="flex gap-1">
                <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage(page - 1)}>Prev</Button>
                <Button variant="outline" size="sm" disabled={page >= totalPages - 1} onClick={() => setPage(page + 1)}>Next</Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Security Monitor */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2 text-base"><Shield className="h-4 w-4 text-primary-600" />Access Security</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between rounded-md border border-neutral-100 px-3 py-2.5">
              <div className="flex items-center gap-2"><AlertTriangle className="h-4 w-4 text-warning" /><span className="text-sm text-neutral-700">Users with failed logins</span></div>
              <span className="text-sm font-bold text-neutral-800">{metrics?.failed_login_attempts_users ?? 0}</span>
            </div>
            <div className="flex items-center justify-between rounded-md border border-neutral-100 px-3 py-2.5">
              <div className="flex items-center gap-2"><Lock className="h-4 w-4 text-danger" /><span className="text-sm text-neutral-700">Currently locked</span></div>
              <span className="text-sm font-bold text-neutral-800">{metrics?.locked ?? 0}</span>
            </div>
            <div className="flex items-center justify-between rounded-md border border-neutral-100 px-3 py-2.5">
              <div className="flex items-center gap-2"><Clock className="h-4 w-4 text-neutral-400" /><span className="text-sm text-neutral-700">Dormant (&gt;30d)</span></div>
              <span className="text-sm font-bold text-neutral-800">{metrics?.dormant ?? 0}</span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2 text-base"><Heart className="h-4 w-4 text-danger" />Healthcare Relationships</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between rounded-md border border-neutral-100 px-3 py-2.5">
              <span className="text-sm text-neutral-700">Patients WITH active consent</span>
              <span className="text-sm font-bold text-success">{metrics?.patients_with_consent ?? 0}</span>
            </div>
            <div className="flex items-center justify-between rounded-md border border-neutral-100 px-3 py-2.5">
              <span className="text-sm text-neutral-700">Patients WITHOUT consent</span>
              <span className="text-sm font-bold text-warning">{metrics?.patients_without_consent ?? 0}</span>
            </div>
            <div className="flex items-center justify-between rounded-md border border-neutral-100 px-3 py-2.5">
              <span className="text-sm text-neutral-700">Doctor access events (7d)</span>
              <span className="text-sm font-bold text-neutral-800">{metrics?.doctor_access_events_7d ?? 0}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* User Detail Dialog */}
      {selectedUser && !actionModal && (
        <Dialog open onClose={() => setSelectedUser(null)} title="User Management" className="max-w-2xl">
          <div className="space-y-4">
            {/* User header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary-50 text-lg font-bold text-primary-700">{selectedUser.full_name.charAt(0).toUpperCase()}</div>
                <div>
                  <p className="font-semibold text-neutral-800">{selectedUser.full_name}</p>
                  <p className="text-sm text-neutral-500">{selectedUser.email}</p>
                </div>
              </div>
              <Badge variant={selectedUser.status === "active" ? "success" : selectedUser.status === "locked" ? "danger" : "warning"}>{selectedUser.status}</Badge>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 border-b border-neutral-200">
              {(["overview", "audit", "consents", "records"] as const).map((tab) => (
                <button key={tab} onClick={() => setDetailTab(tab)} className={`px-3 py-2 text-sm font-medium capitalize ${detailTab === tab ? "border-b-2 border-primary-600 text-primary-700" : "text-neutral-500 hover:text-neutral-700"}`}>{tab}</button>
              ))}
            </div>

            {/* Tab Content */}
            {detailTab === "overview" && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <DetailField label="Role" value={selectedUser.role} />
                  <DetailField label="Status" value={selectedUser.status} />
                  <DetailField label="Risk Level" value={selectedUser.risk_level} />
                  <DetailField label="Failed Logins" value={String(selectedUser.failed_login_attempts)} />
                  <DetailField label="Records" value={String(selectedUser.records_count)} />
                  <DetailField label="Consents" value={String(selectedUser.consents_count)} />
                  <DetailField label="Last Login" value={selectedUser.last_login ? formatDateTime(selectedUser.last_login) : "Never"} />
                  <DetailField label="Registered" value={formatDateTime(selectedUser.created_at)} />
                  <DetailField label="MFA" value={userDetail?.user?.mfa_enabled ? "Enabled" : "Not configured"} />
                  <DetailField label="WebAuthn" value={userDetail?.user?.webauthn_enrolled ? "Enrolled" : "Not enrolled"} />
                </div>
                {/* Action Buttons */}
                <div className="flex flex-wrap gap-2 border-t border-neutral-200 pt-4">
                  {selectedUser.status === "locked" && (
                    <Button size="sm" variant="outline" className="gap-1.5" onClick={() => unlockMutation.mutate(selectedUser.id)}><Unlock className="h-3.5 w-3.5" />Unlock</Button>
                  )}
                  {selectedUser.status === "active" && (
                    <Button size="sm" variant="outline" className="gap-1.5" onClick={() => setActionModal("lock")}><Lock className="h-3.5 w-3.5" />Lock</Button>
                  )}
                  {selectedUser.status === "active" && (
                    <Button size="sm" variant="outline" className="gap-1.5 text-warning" onClick={() => setActionModal("suspend")}><Ban className="h-3.5 w-3.5" />Suspend</Button>
                  )}
                  {selectedUser.status === "suspended" && (
                    <Button size="sm" variant="outline" className="gap-1.5 text-success" onClick={() => activateMutation.mutate(selectedUser.id)}><CheckCircle2 className="h-3.5 w-3.5" />Activate</Button>
                  )}
                  <Button size="sm" variant="outline" className="gap-1.5" onClick={() => setActionModal("resetMfa")}><KeyRound className="h-3.5 w-3.5" />Reset MFA</Button>
                  <Button size="sm" variant="outline" className="gap-1.5 text-danger" onClick={() => setActionModal("delete")}><Trash2 className="h-3.5 w-3.5" />Delete</Button>
                </div>
              </div>
            )}

            {detailTab === "audit" && (
              <div className="max-h-80 space-y-2 overflow-y-auto">
                {userDetail?.audit_history && userDetail.audit_history.length > 0 ? (
                  userDetail.audit_history.map((event) => (
                    <div key={event._id} className="flex items-start justify-between rounded-md border border-neutral-100 px-3 py-2">
                      <div>
                        <p className="text-sm font-medium text-neutral-800">{event.action_type} — {event.resource_type}</p>
                        <p className="text-xs text-neutral-500">{event.reason || "No reason provided"}</p>
                      </div>
                      <div className="text-right">
                        <Badge variant={event.severity === "critical" ? "danger" : event.severity === "warning" ? "warning" : "default"} className="text-[10px]">{event.severity}</Badge>
                        <p className="mt-1 text-[10px] text-neutral-400">{formatDateTime(event.created_at)}</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="py-8 text-center text-sm text-neutral-400">No audit history</p>
                )}
              </div>
            )}

            {detailTab === "consents" && (
              <div className="max-h-80 space-y-2 overflow-y-auto">
                {userDetail?.consents && userDetail.consents.length > 0 ? (
                  userDetail.consents.map((c: Record<string, unknown>) => (
                    <div key={c._id as string} className="flex items-center justify-between rounded-md border border-neutral-100 px-3 py-2">
                      <div>
                        <p className="text-sm font-medium text-neutral-800">{String(c.consent_type).replace(/_/g, " ")}</p>
                        <p className="text-xs text-neutral-500">Granted: {formatDateTime(c.granted_at as string)}</p>
                      </div>
                      <Badge variant={c.status === "active" ? "success" : c.status === "withdrawn" ? "danger" : "warning"}>{c.status as string}</Badge>
                    </div>
                  ))
                ) : (
                  <p className="py-8 text-center text-sm text-neutral-400">No consents found</p>
                )}
              </div>
            )}

            {detailTab === "records" && (
              <div className="max-h-80 space-y-2 overflow-y-auto">
                {userDetail?.records && userDetail.records.length > 0 ? (
                  userDetail.records.map((r: Record<string, unknown>) => (
                    <div key={r._id as string} className="flex items-center justify-between rounded-md border border-neutral-100 px-3 py-2">
                      <div>
                        <p className="text-sm font-medium text-neutral-800">{r.title as string}</p>
                        <p className="text-xs text-neutral-500">{r.record_type as string} • {formatDateTime(r.created_at as string)}</p>
                      </div>
                      <Badge variant={r.redacted ? "danger" : "success"}>{r.redacted ? "Redacted" : "Active"}</Badge>
                    </div>
                  ))
                ) : (
                  <p className="py-8 text-center text-sm text-neutral-400">No records found</p>
                )}
              </div>
            )}

            <div className="flex justify-end pt-2">
              <Button variant="outline" onClick={() => setSelectedUser(null)}>Close</Button>
            </div>
          </div>
        </Dialog>
      )}

      {/* Action Modals */}
      {actionModal === "lock" && selectedUser && (
        <Dialog open onClose={() => setActionModal(null)} title="Lock Account" className="max-w-md">
          <div className="space-y-4">
            <p className="text-sm text-neutral-600">Lock <strong>{selectedUser.full_name}</strong>'s account? They will be unable to log in.</p>
            <Input placeholder="Reason for locking..." value={actionReason} onChange={(e) => setActionReason(e.target.value)} />
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setActionModal(null)}>Cancel</Button>
              <Button variant="default" className="bg-warning text-white" onClick={() => lockMutation.mutate({ userId: selectedUser.id, reason: actionReason || "Admin action" })} disabled={lockMutation.isPending}>
                {lockMutation.isPending ? "Locking..." : "Lock Account"}
              </Button>
            </div>
          </div>
        </Dialog>
      )}

      {actionModal === "suspend" && selectedUser && (
        <Dialog open onClose={() => setActionModal(null)} title="Suspend Account" className="max-w-md">
          <div className="space-y-4">
            <p className="text-sm text-neutral-600">Suspend <strong>{selectedUser.full_name}</strong>'s account indefinitely?</p>
            <Input placeholder="Reason for suspension..." value={actionReason} onChange={(e) => setActionReason(e.target.value)} />
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setActionModal(null)}>Cancel</Button>
              <Button variant="default" className="bg-danger text-white" onClick={() => suspendMutation.mutate({ userId: selectedUser.id, reason: actionReason || "Admin action" })} disabled={suspendMutation.isPending}>
                {suspendMutation.isPending ? "Suspending..." : "Suspend Account"}
              </Button>
            </div>
          </div>
        </Dialog>
      )}

      {actionModal === "resetMfa" && selectedUser && (
        <Dialog open onClose={() => setActionModal(null)} title="Reset MFA" className="max-w-md">
          <div className="space-y-4">
            <p className="text-sm text-neutral-600">Reset MFA for <strong>{selectedUser.full_name}</strong>? They will need to re-enroll.</p>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setActionModal(null)}>Cancel</Button>
              <Button variant="default" onClick={() => resetMfaMutation.mutate(selectedUser.id)} disabled={resetMfaMutation.isPending}>
                {resetMfaMutation.isPending ? "Resetting..." : "Reset MFA"}
              </Button>
            </div>
          </div>
        </Dialog>
      )}

      {actionModal === "delete" && selectedUser && (
        <Dialog open onClose={() => setActionModal(null)} title="Delete User" className="max-w-md">
          <div className="space-y-4">
            <div className="rounded-md bg-danger/10 p-3">
              <p className="text-sm font-medium text-danger">⚠️ This action is irreversible</p>
              <p className="mt-1 text-xs text-danger/80">Deleting <strong>{selectedUser.full_name}</strong> will archive their data and remove their account permanently.</p>
            </div>
            <Input placeholder="Reason for deletion (required)..." value={actionReason} onChange={(e) => setActionReason(e.target.value)} />
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setActionModal(null)}>Cancel</Button>
              <Button variant="default" className="bg-danger text-white" disabled={!actionReason || deleteMutation.isPending} onClick={() => deleteMutation.mutate({ userId: selectedUser.id, reason: actionReason })}>
                {deleteMutation.isPending ? "Deleting..." : "Delete User"}
              </Button>
            </div>
          </div>
        </Dialog>
      )}
    </div>
  );
}

function DetailField({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-neutral-50 p-2.5">
      <p className="text-[10px] font-medium uppercase tracking-wide text-neutral-400">{label}</p>
      <p className="mt-0.5 text-sm font-medium text-neutral-800 capitalize">{value}</p>
    </div>
  );
}

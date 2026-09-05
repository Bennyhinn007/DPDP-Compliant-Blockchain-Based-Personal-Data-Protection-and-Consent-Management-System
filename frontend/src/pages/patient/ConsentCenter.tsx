/**
 * Consent Center.
 *
 * Grant, modify, and withdraw consents with status indicators.
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, ShieldCheck } from "lucide-react";
import { consentService } from "@/services/consentService";
import { getErrorMessage } from "@/services/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog } from "@/components/ui/dialog";
import { PageHero } from "@/components/shared/PageHero";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { CONSENT_LABELS, CONSENT_ICONS, ALL_CONSENT_TYPES, statusVariant } from "@/lib/consentMeta";
import { formatDate } from "@/lib/utils";
import type { Consent, ConsentType } from "@/types";

export function ConsentCenter() {
  const queryClient = useQueryClient();
  const [grantOpen, setGrantOpen] = useState(false);
  const [modifyTarget, setModifyTarget] = useState<Consent | null>(null);
  const [withdrawTarget, setWithdrawTarget] = useState<Consent | null>(null);
  const [msg, setMsg] = useState("");

  const { data: consents = [] } = useQuery({
    queryKey: ["consents"],
    queryFn: consentService.list,
  });

  const invalidate = (m: string) => {
    setMsg(m);
    queryClient.invalidateQueries({ queryKey: ["consents"] });
  };

  return (
    <div className="space-y-6">
      <PageHero
        title="Consent Management Center"
        subtitle="Control who can access your data and for what purpose"
        icon={ShieldCheck}
        actions={
          <Button variant="accent" onClick={() => setGrantOpen(true)}>
            <Plus className="h-4 w-4" />
            Grant Consent
          </Button>
        }
      />

      {msg && <div className="rounded-md bg-success/10 px-4 py-3 text-sm text-success">{msg}</div>}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {consents.length === 0 ? (
          <Card className="col-span-full">
            <CardContent className="py-12 text-center text-sm text-neutral-400">
              No consents yet. Click "Grant Consent" to begin.
            </CardContent>
          </Card>
        ) : (
          consents.map((c) => (
            <Card key={c._id}>
              <CardContent className="p-5">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-2xl">{CONSENT_ICONS[c.consent_type as ConsentType]}</span>
                    <div>
                      <h3 className="text-sm font-semibold text-neutral-800">
                        {CONSENT_LABELS[c.consent_type as ConsentType]}
                      </h3>
                      <p className="text-xs text-neutral-400">{c.processing_entity_name}</p>
                    </div>
                  </div>
                  <Badge variant={statusVariant(c.status)}>{c.status}</Badge>
                </div>

                <p className="mt-3 text-xs text-neutral-500">{c.purpose_description}</p>

                <div className="mt-3 flex flex-wrap gap-1">
                  {c.data_categories_in_scope.slice(0, 3).map((cat) => (
                    <Badge key={cat} variant="neutral">{cat}</Badge>
                  ))}
                </div>

                <div className="mt-3 text-xs text-neutral-400">
                  {c.status === "active" ? `Expires ${formatDate(c.expires_at)}` : `Granted ${formatDate(c.granted_at)}`}
                </div>

                {c.status === "active" && (
                  <div className="mt-4 flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => setModifyTarget(c)}>
                      Modify
                    </Button>
                    <Button variant="danger" size="sm" onClick={() => setWithdrawTarget(c)}>
                      Withdraw
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {grantOpen && (
        <GrantDialog
          existing={consents}
          onClose={() => setGrantOpen(false)}
          onSuccess={(m) => {
            invalidate(m);
            setGrantOpen(false);
          }}
        />
      )}

      {modifyTarget && (
        <ModifyDialog
          consent={modifyTarget}
          onClose={() => setModifyTarget(null)}
          onSuccess={(m) => {
            invalidate(m);
            setModifyTarget(null);
          }}
        />
      )}

      {withdrawTarget && (
        <WithdrawDialog
          consent={withdrawTarget}
          onClose={() => setWithdrawTarget(null)}
          onSuccess={(m) => {
            invalidate(m);
            setWithdrawTarget(null);
          }}
        />
      )}
    </div>
  );
}

function GrantDialog({
  existing,
  onClose,
  onSuccess,
}: {
  existing: Consent[];
  onClose: () => void;
  onSuccess: (msg: string) => void;
}) {
  const activeTypes = new Set(existing.filter((c) => c.status === "active").map((c) => c.consent_type));
  const available = ALL_CONSENT_TYPES.filter((t) => !activeTypes.has(t));

  const [consentType, setConsentType] = useState<ConsentType>(available[0] || "healthcare_treatment");
  const [entity, setEntity] = useState("");
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: () => consentService.grant(consentType, entity, 365),
    onSuccess: () => onSuccess("Consent granted. Receipt generated and anchored on blockchain."),
    onError: (err) => setError(getErrorMessage(err)),
  });

  return (
    <Dialog open onClose={onClose} title="Grant Consent" description="Authorize data access for a specific purpose">
      <div className="space-y-4">
        {error && <div className="rounded-md bg-danger/5 px-3 py-2 text-sm text-danger">{error}</div>}
        <div className="space-y-1.5">
          <Label htmlFor="consent-type">Consent Type</Label>
          <select
            id="consent-type"
            value={consentType}
            onChange={(e) => setConsentType(e.target.value as ConsentType)}
            className="flex h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
          >
            {available.map((t) => (
              <option key={t} value={t}>{CONSENT_LABELS[t]}</option>
            ))}
          </select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="entity">Processing Entity</Label>
          <Input
            id="entity"
            value={entity}
            onChange={(e) => setEntity(e.target.value)}
            placeholder="e.g., Apollo Healthcare"
          />
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={() => mutation.mutate()} disabled={mutation.isPending || entity.length < 2}>
            {mutation.isPending ? "Granting..." : "Grant Consent"}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}

function ModifyDialog({
  consent,
  onClose,
  onSuccess,
}: {
  consent: Consent;
  onClose: () => void;
  onSuccess: (msg: string) => void;
}) {
  const [scope, setScope] = useState(consent.data_categories_in_scope.join(", "));
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      consentService.modify(
        consent._id,
        scope.split(",").map((s) => s.trim()).filter(Boolean),
        reason
      ),
    onSuccess: () => onSuccess("Consent scope modified successfully."),
    onError: (err) => setError(getErrorMessage(err)),
  });

  return (
    <Dialog open onClose={onClose} title="Modify Consent" description="Adjust the data categories in scope">
      <div className="space-y-4">
        {error && <div className="rounded-md bg-danger/5 px-3 py-2 text-sm text-danger">{error}</div>}
        <div className="space-y-1.5">
          <Label htmlFor="scope">Data Categories (comma-separated)</Label>
          <Input id="scope" value={scope} onChange={(e) => setScope(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="modify-reason">Reason</Label>
          <Textarea
            id="modify-reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Why are you modifying this consent?"
          />
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={() => mutation.mutate()} disabled={mutation.isPending || reason.length < 5}>
            {mutation.isPending ? "Saving..." : "Save Changes"}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}

function WithdrawDialog({
  consent,
  onClose,
  onSuccess,
}: {
  consent: Consent;
  onClose: () => void;
  onSuccess: (msg: string) => void;
}) {
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: () => consentService.withdraw(consent._id, reason),
    onSuccess: () => onSuccess("Consent withdrawn. Access revoked immediately."),
    onError: (err) => setError(getErrorMessage(err)),
  });

  return (
    <Dialog open onClose={onClose} title="Withdraw Consent" description="Immediately revoke data access">
      <div className="space-y-4">
        {error && <div className="rounded-md bg-danger/5 px-3 py-2 text-sm text-danger">{error}</div>}
        <div className="rounded-md bg-warning/10 px-3 py-2.5 text-sm text-warning">
          Withdrawing <strong>{CONSENT_LABELS[consent.consent_type as ConsentType]}</strong> consent
          will immediately revoke all data access for {consent.processing_entity_name}.
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="withdraw-reason">Reason (optional)</Label>
          <Textarea
            id="withdraw-reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Optional reason for withdrawal"
          />
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="danger" onClick={() => mutation.mutate()} disabled={mutation.isPending}>
            {mutation.isPending ? "Withdrawing..." : "Confirm Withdrawal"}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}

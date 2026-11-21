/**
 * Consent Center.
 *
 * Grant, modify, and withdraw consents with status indicators.
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, ShieldCheck } from "lucide-react";
import { consentService, type Recipient, type ScopeOptions } from "@/services/consentService";
import { patientService } from "@/services/patientService";
import { Link } from "react-router-dom";
import { getErrorMessage } from "@/services/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog } from "@/components/ui/dialog";
import { PageHero } from "@/components/shared/PageHero";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { CONSENT_LABELS, CONSENT_ICONS, ALL_CONSENT_TYPES, needsRegrant, statusVariant } from "@/lib/consentMeta";
import { formatDate, humanize } from "@/lib/utils";
import type { Consent, ConsentType } from "@/types";

export function ConsentCenter() {
  const queryClient = useQueryClient();
  const [grantOpen, setGrantOpen] = useState(false);
  const [modifyTarget, setModifyTarget] = useState<Consent | null>(null);
  const [withdrawTarget, setWithdrawTarget] = useState<Consent | null>(null);
  const [msg, setMsg] = useState("");

  const consentsQuery = useQuery({
    queryKey: ["consents"],
    queryFn: consentService.list,
  });
  const consents = consentsQuery.data ?? [];
  const regrant = consents.filter(needsRegrant);

  const receiptsQuery = useQuery({ queryKey: ["receipts"], queryFn: consentService.receipts });
  const profile = useQuery({ queryKey: ["profile"], queryFn: patientService.getProfile });
  const savedAllergies = Array.isArray(profile.data?.allergies) ? profile.data.allergies : null;

  const options = useQuery({ queryKey: ["consent-scope-options"], queryFn: consentService.scopeOptions });

  const invalidate = (m: string) => {
    setMsg(m);
    queryClient.invalidateQueries({ queryKey: ["consents"] });
    queryClient.invalidateQueries({ queryKey: ["timeline"] });
    queryClient.invalidateQueries({ queryKey: ["receipts"] });
  };

  return (
    <div className="space-y-6">
      <PageHero
        title="Consent Management Center"
        subtitle="Control who can access your data and for what purpose"
        icon={ShieldCheck}
        actions={
          <Button variant="accent" disabled={!options.data} onClick={() => setGrantOpen(true)}>
            <Plus className="h-4 w-4" />
            Grant Consent
          </Button>
        }
      />

      {options.isError && <p role="alert">Sharing options could not be loaded. <button className="underline" onClick={() => options.refetch()}>Retry</button></p>}
      {msg && <div className="rounded-md bg-success/10 px-4 py-3 text-sm text-success">{msg}</div>}

      {regrant.length > 0 && (
        <div role="alert" className="rounded-md bg-warning/10 px-4 py-3 text-sm text-warning">
          <strong>Re-grant needed.</strong> These older treatment grants have no linked doctor or hospital, so no chart is shared.
          Create a new grant for: {regrant.map((c) => c.processing_entity_name).join(", ")}.
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {consentsQuery.isLoading ? (
          <Card className="col-span-full">
            <CardContent className="py-12 text-center text-sm text-neutral-400">Loading your consents…</CardContent>
          </Card>
        ) : consentsQuery.isError ? (
          <Card className="col-span-full">
            <CardContent role="alert" className="py-12 text-center text-sm text-danger">
              Your consents could not be loaded.{" "}
              <button className="underline" onClick={() => consentsQuery.refetch()}>Retry</button>
            </CardContent>
          </Card>
        ) : consents.length === 0 ? (
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
                  {(Array.isArray(c.data_categories_in_scope) ? c.data_categories_in_scope.filter((cat) => typeof cat === "string") : []).map((cat) => (
                    <Badge key={cat} variant="neutral">{humanize(cat)}</Badge>
                  ))}
                </div>

                {c.data_categories_in_scope?.includes("allergies") && (
                  <p className="mt-2 text-sm">
                    Selected allergies:{" "}
                    {c.selected_allergies?.length
                      ? c.selected_allergies.map((a, i) => (
                          <span key={a}>
                            {i > 0 && ", "}
                            {a}
                            {savedAllergies && !savedAllergies.includes(a) && " (no longer saved, not shared)"}
                          </span>
                        ))
                      : "None selected"}
                  </p>
                )}
                {needsRegrant(c) && (
                  <p className="mt-2 rounded-md bg-warning/10 px-3 py-2 text-sm font-medium text-warning">
                    Re-grant needed: this older grant has no linked recipient, so no chart is shared. Withdraw it and create a new grant.
                  </p>
                )}
                <div className="mt-3 text-xs text-neutral-400">
                  {c.status === "active" ? `Expires ${formatDate(c.expires_at)}` : `Granted ${formatDate(c.granted_at)}`}
                </div>

                {c.status === "active" && (
                  <div className="mt-4 flex gap-2">
                    {!needsRegrant(c) && (
                      <Button variant="outline" size="sm" disabled={!options.data} onClick={() => setModifyTarget(c)}>
                        Modify
                      </Button>
                    )}
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

      <section aria-labelledby="receipts-heading" className="space-y-3">
        <h2 id="receipts-heading" className="text-base font-semibold text-neutral-800">Consent receipts</h2>
        {receiptsQuery.isLoading ? (
          <p className="text-sm text-neutral-400">Loading receipts…</p>
        ) : receiptsQuery.isError ? (
          <p role="alert" className="text-sm text-danger">
            Receipts could not be loaded.{" "}
            <button className="underline" onClick={() => receiptsQuery.refetch()}>Retry</button>
          </p>
        ) : (receiptsQuery.data ?? []).length === 0 ? (
          <p className="text-sm text-neutral-400">No receipts yet. One is issued each time you grant, modify or withdraw consent.</p>
        ) : (
          <ul className="space-y-2">
            {(receiptsQuery.data ?? []).map((r) => (
              <li key={r._id} className="rounded-md border border-neutral-200 p-3 text-sm">
                <span className="font-medium">{humanize(r.action_type)}</span>
                {" · "}{r.processing_entity_name}
                {" · "}Allergies: {r.selected_allergies?.length ? r.selected_allergies.join(", ") : "none"}
                {" · "}{formatDate(r.issued_at)}
              </li>
            ))}
          </ul>
        )}
      </section>

      {grantOpen && options.data && (
        <GrantDialog
          options={options.data}
          onClose={() => setGrantOpen(false)}
          onSuccess={(m) => {
            invalidate(m);
            setGrantOpen(false);
          }}
        />
      )}

      {modifyTarget && options.data && (
        <ModifyDialog
          options={options.data[modifyTarget.consent_type]}
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

function ScopeChoices({ options, value, onChange }: {
  options: string[];
  value: string[];
  onChange: (categories: string[]) => void;
}) {
  if (options.length === 0) return <p className="text-sm">This purpose uses aggregate data only.</p>;
  return (
    <fieldset className="space-y-2">
      <legend className="mb-2 text-sm font-medium">Data you agree to share</legend>
      {options.map((category) => (
        <label key={category} className="flex items-start gap-2 text-sm">
          <input className="mt-1" type="checkbox" checked={value.includes(category)}
            onChange={(event) => onChange(event.target.checked
              ? [...value, category] : value.filter((item) => item !== category))} />
          <span>{humanize(category)}
            {category === "medical_history" && <small className="block text-neutral-500">Includes blood group and full consultation notes, diagnoses, symptoms and treatment notes.</small>}
            {category === "allergies" && <small className="block text-neutral-500">Choose individual entries from your saved profile.</small>}
          </span>
        </label>
      ))}
    </fieldset>
  );
}

const selectClass = "h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm";

function AllergyChoices({ value, onChange }: { value: string[]; onChange: (items: string[]) => void }) {
  const profile = useQuery({ queryKey: ["profile"], queryFn: patientService.getProfile });
  const saved = Array.isArray(profile.data?.allergies) ? profile.data.allergies : [];
  return <fieldset className="space-y-2 rounded-md border p-3">
    <legend className="px-1 text-sm font-medium">Which allergies can they see?</legend>
    {profile.isLoading && <p className="text-sm">Loading your allergies…</p>}
    {profile.isError && <button className="underline" onClick={() => profile.refetch()}>Retry loading your allergies</button>}
    {profile.data && !saved.length && <p className="text-sm">Your profile has no saved allergies.</p>}
    {Array.from(new Set([...saved, ...value])).sort((a, b) => a.localeCompare(b)).map(item =>
      <label key={item} className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={value.includes(item)} onChange={e => onChange(e.target.checked
          ? [...value, item] : value.filter(a => a !== item))} />
        {item}{!saved.includes(item) && profile.data && " (removed from profile; deselect to save)"}
      </label>)}
    <Link to="/my-data" className="text-sm text-primary-700 underline">Manage my saved allergies</Link>
  </fieldset>;
}

function GrantDialog({
  options,
  onClose,
  onSuccess,
}: {
  options: ScopeOptions;
  onClose: () => void;
  onSuccess: (msg: string) => void;
}) {
  const [consentType, setConsentType] = useState<ConsentType>("healthcare_treatment");
  const [scope, setScope] = useState<string[]>([]);
  const [allergies, setAllergies] = useState<string[]>([]);
  const [hospitalId, setHospitalId] = useState("");
  const [recipientId, setRecipientId] = useState("");
  const [entity, setEntity] = useState("");
  const directory = useQuery({ queryKey: ["providers"], queryFn: consentService.providers });
  const hospital = directory.data?.find(h => h.id === hospitalId);
  const doctor = hospital?.doctors.find(d => d.id === recipientId);
  const namedEntity = consentType !== "healthcare_treatment" && hospitalId === "other";
  let recipient: Recipient | null = null;
  if (hospital && doctor) recipient = { kind: "doctor", hospital_id: hospital.id, doctor_id: doctor.id };
  else if (hospital?.hospital_grant && recipientId === "hospital") recipient = { kind: "hospital", hospital_id: hospital.id };
  const hasRecipient = namedEntity ? entity.trim().length >= 2 : Boolean(recipient);
  const sharesAllergies = scope.includes("allergies");
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: () => consentService.grant(consentType, entity, 365, scope, recipient, sharesAllergies ? allergies : []),
    onSuccess: () => onSuccess("Consent granted. Your receipt is listed under Consent receipts."),
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
            onChange={(e) => { setConsentType(e.target.value as ConsentType); setScope([]); setAllergies([]); setHospitalId(""); setRecipientId(""); }}
            className="flex h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
          >
            {ALL_CONSENT_TYPES.map((t) => (
              <option key={t} value={t}>{CONSENT_LABELS[t]}</option>
            ))}
          </select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="hospital">Hospital or doctor list</Label>
          <select id="hospital" className={selectClass} value={hospitalId}
            onChange={e => { setHospitalId(e.target.value); setRecipientId(""); }}>
            <option value="">Choose a list</option>
            {directory.data?.map(h => <option key={h.id} value={h.id}>{h.name}</option>)}
            {consentType !== "healthcare_treatment" && <option value="other">Other organization</option>}
          </select>
          {directory.isError && <p role="alert">Directory unavailable. <button className="underline" onClick={() => directory.refetch()}>Retry</button></p>}
        </div>
        {namedEntity && <div><Label htmlFor="entity">Organization name</Label>
          <Input id="entity" value={entity} onChange={e => setEntity(e.target.value)} /></div>}
        {hospital && <div className="space-y-1.5">
          <Label htmlFor="recipient">Who may receive this data?</Label>
          <select id="recipient" className={selectClass} value={recipientId} onChange={e => setRecipientId(e.target.value)}>
            <option value="">Choose a recipient</option>
            {hospital.hospital_grant && <option value="hospital">All affiliated doctors at {hospital.name}</option>}
            {hospital.doctors.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
          {consentType === "healthcare_treatment" && recipient && <p className="text-xs text-neutral-600">
            An active grant for an individual doctor takes priority over a grant for their hospital.
          </p>}
        </div>}
        <ScopeChoices options={options[consentType]} value={scope} onChange={setScope} />
        {sharesAllergies && <AllergyChoices value={allergies} onChange={setAllergies} />}
        <p className="text-xs text-neutral-500">Consent expires in 365 days. You can withdraw it at any time.</p>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={() => mutation.mutate()} disabled={mutation.isPending || !hasRecipient || (sharesAllergies && !allergies.length) || (options[consentType].length > 0 && !scope.length)}>
            {mutation.isPending ? "Granting..." : "Grant Consent"}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}

function ModifyDialog({
  options,
  consent,
  onClose,
  onSuccess,
}: {
  options: string[];
  consent: Consent;
  onClose: () => void;
  onSuccess: (msg: string) => void;
}) {
  const [scope, setScope] = useState(() => options.filter((key) => Array.isArray(consent.data_categories_in_scope) && consent.data_categories_in_scope.includes(key)));
  const [allergies, setAllergies] = useState(consent.selected_allergies ?? []);
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      consentService.modify(
        consent._id,
        scope,
        reason,
        scope.includes("allergies") ? allergies : []
      ),
    onSuccess: () => onSuccess("Consent scope modified successfully."),
    onError: (err) => setError(getErrorMessage(err)),
  });

  return (
    <Dialog open onClose={onClose} title="Modify Consent" description={consent.processing_entity_name}>
      <div className="space-y-4">
        {error && <div className="rounded-md bg-danger/5 px-3 py-2 text-sm text-danger">{error}</div>}
        <ScopeChoices options={options} value={scope} onChange={setScope} />
        {scope.includes("allergies") && <AllergyChoices value={allergies} onChange={setAllergies} />}
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
          <Button onClick={() => mutation.mutate()} disabled={mutation.isPending || reason.trim().length < 5 || (scope.includes("allergies") && !allergies.length) || (options.length > 0 && !scope.length)}>
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
          will end this grant for {consent.processing_entity_name}. Other active grants still apply.
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

/**
 * Personal Data Center.
 *
 * View profile, data categories, download data, request correction/erasure.
 * Includes live-location capture for the Address field.
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Pencil, Trash2, ShieldCheck, User, FileText, Eye, MapPin } from "lucide-react";
import { patientService } from "@/services/patientService";
import { getErrorMessage } from "@/services/api";
import { getLiveLocation, geolocationErrorMessage, type LiveLocation } from "@/lib/geolocation";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ExportDropdown } from "@/components/shared/ExportDropdown";
import { formatDate, humanize } from "@/lib/utils";
import type { HealthcareRecord } from "@/types";

export function PersonalDataCenter() {
  const queryClient = useQueryClient();
  const [correctTarget, setCorrectTarget] = useState<HealthcareRecord | null>(null);
  const [eraseTarget, setEraseTarget] = useState<HealthcareRecord | null>(null);
  const [viewTarget, setViewTarget] = useState<HealthcareRecord | null>(null);
  const [actionMsg, setActionMsg] = useState("");
  const [locating, setLocating] = useState(false);
  const [locationDraft, setLocationDraft] = useState<LiveLocation | null>(null);
  const [editedAddress, setEditedAddress] = useState("");

  const { data: profile } = useQuery({
    queryKey: ["profile"],
    queryFn: patientService.getProfile,
  });

  const { data: records = [] } = useQuery({
    queryKey: ["records"],
    queryFn: patientService.listRecords,
  });

  const updateAddressMutation = useMutation({
    mutationFn: (address: string) => patientService.updateProfile({ address }),
    onSuccess: () => {
      setActionMsg("Address saved. Stored encrypted (AES-256).");
      setLocationDraft(null);
      queryClient.invalidateQueries({ queryKey: ["profile"] });
    },
    onError: (err) => setActionMsg(getErrorMessage(err)),
  });

  // Step 1: detect location and open a confirmation dialog (do NOT auto-save).
  const handleUseLiveLocation = async () => {
    setLocating(true);
    setActionMsg("");
    try {
      const loc = await getLiveLocation();
      setLocationDraft(loc);
      setEditedAddress(loc.address);
    } catch (err) {
      setActionMsg(geolocationErrorMessage(err));
    } finally {
      setLocating(false);
    }
  };

  const dataCategories = profile?.allergies?.length
    ? ["Personal Info", "Contact Info", "Medical History", "Allergies"]
    : ["Personal Info", "Contact Info"];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-800">My Personal Data Center</h1>
          <p className="mt-1 text-sm text-neutral-500">
            View, manage, and exercise control over your personal data
          </p>
        </div>
        <ExportDropdown />
      </div>

      {actionMsg && (
        <div className="rounded-md bg-success/10 px-4 py-3 text-sm text-success">{actionMsg}</div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Profile */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5 text-primary-600" />
              Profile Information
            </CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="Full Name" value={profile?.full_name} />
              <Field label="Phone Number" value={profile?.phone_number} />
              <Field label="Blood Group" value={profile?.blood_group} />
              <Field label="Identity Type" value={profile?.identity_type ? humanize(profile.identity_type) : null} />
              <div className="sm:col-span-2">
                <dt className="text-xs font-medium text-neutral-500">Address</dt>
                <dd className="mt-0.5 flex flex-wrap items-center justify-between gap-2 text-sm text-neutral-800">
                  <span className="flex-1">{profile?.address || "—"}</span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleUseLiveLocation}
                    disabled={locating || updateAddressMutation.isPending}
                    className="shrink-0 gap-1.5"
                  >
                    <MapPin className="h-3.5 w-3.5" />
                    {locating
                      ? "Locating..."
                      : updateAddressMutation.isPending
                        ? "Saving..."
                        : "Use Current Location"}
                  </Button>
                </dd>
              </div>
              <Field
                label="Allergies"
                value={profile?.allergies?.length ? profile.allergies.join(", ") : "None recorded"}
              />
            </dl>
          </CardContent>
        </Card>

        {/* Privacy summary */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-success" />
              Privacy Summary
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="rounded-md bg-success/5 p-3">
              <p className="text-xs font-medium text-success">Encryption</p>
              <p className="text-sm text-neutral-600">AES-256 at rest</p>
            </div>
            <div className="rounded-md bg-primary-50 p-3">
              <p className="text-xs font-medium text-primary-700">Data Residency</p>
              <p className="text-sm text-neutral-600">India (DPDP compliant)</p>
            </div>
            <div>
              <p className="mb-2 text-xs font-medium text-neutral-500">Data Categories Stored</p>
              <div className="flex flex-wrap gap-1.5">
                {dataCategories.map((cat) => (
                  <Badge key={cat} variant="neutral">{cat}</Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Health records with correction/erasure */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary-600" />
            Health Records
          </CardTitle>
        </CardHeader>
        <CardContent>
          {records.length === 0 ? (
            <p className="py-8 text-center text-sm text-neutral-400">No health records yet</p>
          ) : (
            <div className="space-y-3">
              {records.map((rec) => (
                <div
                  key={rec._id}
                  className="flex items-center justify-between rounded-lg border border-neutral-200 p-4"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-neutral-700">{rec.title}</span>
                      {rec.redacted && <Badge variant="danger">Redacted</Badge>}
                      <Badge variant="neutral">{humanize(rec.record_type)}</Badge>
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-xs text-neutral-400">
                      {rec.symptoms && rec.symptoms.length > 0 && rec.symptoms[0] !== "none" && (
                        <span>{rec.symptoms.join(" • ")}</span>
                      )}
                      <span>{formatDate(rec.created_at)}</span>
                      {rec.verification_hash && (
                        <span className="flex items-center gap-0.5 text-success">
                          <ShieldCheck className="h-3 w-3" /> Verified
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setViewTarget(rec)}
                    >
                      <Eye className="h-3.5 w-3.5" />
                      View
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCorrectTarget(rec)}
                      disabled={rec.redacted}
                    >
                      <Pencil className="h-3.5 w-3.5" />
                      Correct
                    </Button>
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => setEraseTarget(rec)}
                      disabled={rec.redacted}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      Erase
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Correction dialog */}
      {correctTarget && (
        <CorrectionDialog
          record={correctTarget}
          onClose={() => setCorrectTarget(null)}
          onSuccess={(msg) => {
            setActionMsg(msg);
            setCorrectTarget(null);
            queryClient.invalidateQueries({ queryKey: ["records"] });
          }}
        />
      )}

      {/* Erasure dialog */}
      {eraseTarget && (
        <ErasureDialog
          record={eraseTarget}
          onClose={() => setEraseTarget(null)}
          onSuccess={(msg) => {
            setActionMsg(msg);
            setEraseTarget(null);
            queryClient.invalidateQueries({ queryKey: ["records"] });
          }}
        />
      )}

      {/* Location Confirmation Dialog */}
      {locationDraft && (
        <Dialog
          open
          onClose={() => setLocationDraft(null)}
          title="Confirm Your Location"
          description="Review the detected address before saving. You can edit it if it's not accurate."
          className="max-w-lg"
        >
          <div className="space-y-4">
            {/* Accuracy notice */}
            <div
              className={`rounded-md px-3 py-2.5 text-sm ${
                locationDraft.accuracy <= 100
                  ? "bg-success/10 text-success"
                  : "bg-warning/10 text-warning"
              }`}
            >
              {locationDraft.accuracy <= 100
                ? `Good accuracy — within ~${Math.round(locationDraft.accuracy)} meters.`
                : `Low accuracy — approximately ${(locationDraft.accuracy / 1000).toFixed(1)} km. ` +
                  `Your device likely used WiFi/IP location instead of GPS. Please verify or edit the address below.`}
            </div>

            {/* Map preview */}
            <div className="overflow-hidden rounded-md border border-neutral-200">
              <iframe
                title="Location preview"
                width="100%"
                height="220"
                loading="lazy"
                style={{ border: 0 }}
                src={`https://www.openstreetmap.org/export/embed.html?bbox=${
                  locationDraft.longitude - 0.01
                }%2C${locationDraft.latitude - 0.01}%2C${
                  locationDraft.longitude + 0.01
                }%2C${locationDraft.latitude + 0.01}&layer=mapnik&marker=${
                  locationDraft.latitude
                }%2C${locationDraft.longitude}`}
              />
            </div>

            <div className="text-xs text-neutral-400">
              Coordinates: {locationDraft.latitude.toFixed(6)}, {locationDraft.longitude.toFixed(6)}
            </div>

            {/* Editable address */}
            <div className="space-y-1.5">
              <Label htmlFor="detected-address">Address</Label>
              <Textarea
                id="detected-address"
                value={editedAddress}
                onChange={(e) => setEditedAddress(e.target.value)}
                placeholder="Detected address"
              />
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setLocationDraft(null)}>
                Cancel
              </Button>
              <Button
                onClick={() => updateAddressMutation.mutate(editedAddress)}
                disabled={updateAddressMutation.isPending || editedAddress.trim().length < 3}
              >
                {updateAddressMutation.isPending ? "Saving..." : "Save Address"}
              </Button>
            </div>
          </div>
        </Dialog>
      )}

      {/* View Record Modal */}
      {viewTarget && (
        <Dialog open onClose={() => setViewTarget(null)} title={viewTarget.title} className="max-w-lg">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Badge variant="neutral">{humanize(viewTarget.record_type)}</Badge>
              <span className="text-xs text-neutral-400">{formatDate(viewTarget.created_at)}</span>
              {viewTarget.verification_hash && (
                <Badge variant="success">Blockchain Verified</Badge>
              )}
            </div>
            {viewTarget.description && (
              <div>
                <p className="text-xs font-medium text-neutral-500">Description</p>
                <p className="mt-1 text-sm text-neutral-700">{viewTarget.description}</p>
              </div>
            )}
            {viewTarget.symptoms && viewTarget.symptoms.length > 0 && viewTarget.symptoms[0] !== "none" && (
              <div>
                <p className="text-xs font-medium text-neutral-500">Symptoms</p>
                <p className="mt-1 text-sm text-neutral-700">{viewTarget.symptoms.join(", ")}</p>
              </div>
            )}
            {viewTarget.diagnosis_codes && viewTarget.diagnosis_codes.length > 0 && (
              <div>
                <p className="text-xs font-medium text-neutral-500">Diagnosis Codes</p>
                <p className="mt-1 font-mono text-sm text-neutral-700">{viewTarget.diagnosis_codes.join(", ")}</p>
              </div>
            )}
            {viewTarget.treatment_notes && (
              <div>
                <p className="text-xs font-medium text-neutral-500">Treatment Notes</p>
                <p className="mt-1 text-sm text-neutral-700">{viewTarget.treatment_notes}</p>
              </div>
            )}
          </div>
        </Dialog>
      )}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <dt className="text-xs font-medium text-neutral-500">{label}</dt>
      <dd className="mt-0.5 text-sm text-neutral-800">{value || "—"}</dd>
    </div>
  );
}

function CorrectionDialog({
  record,
  onClose,
  onSuccess,
}: {
  record: HealthcareRecord;
  onClose: () => void;
  onSuccess: (msg: string) => void;
}) {
  const [title, setTitle] = useState(record.title);
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: () => patientService.correctRecord(record._id, { title }, reason),
    onSuccess: () => onSuccess("Record corrected successfully. Blockchain re-anchored."),
    onError: (err) => setError(getErrorMessage(err)),
  });

  return (
    <Dialog open onClose={onClose} title="Request Correction" description="DPDP Section 12 - Right to Correction">
      <div className="space-y-4">
        {error && <div className="rounded-md bg-danger/5 px-3 py-2 text-sm text-danger">{error}</div>}
        <div className="space-y-1.5">
          <Label htmlFor="title">Corrected Title</Label>
          <Input id="title" value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="reason">Reason for Correction</Label>
          <Textarea
            id="reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Explain why this correction is needed (min 5 characters)"
          />
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={() => mutation.mutate()} disabled={mutation.isPending || reason.length < 5}>
            {mutation.isPending ? "Submitting..." : "Submit Correction"}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}

function ErasureDialog({
  record,
  onClose,
  onSuccess,
}: {
  record: HealthcareRecord;
  onClose: () => void;
  onSuccess: (msg: string) => void;
}) {
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      patientService.eraseRecord(record._id, ["title", "description", "diagnosis_codes", "symptoms", "treatment_notes"], reason),
    onSuccess: () => onSuccess("Record erased. Sensitive data redacted with chameleon hash proof."),
    onError: (err) => setError(getErrorMessage(err)),
  });

  return (
    <Dialog open onClose={onClose} title="Request Erasure" description="DPDP Section 12 - Right to Erasure">
      <div className="space-y-4">
        {error && <div className="rounded-md bg-danger/5 px-3 py-2 text-sm text-danger">{error}</div>}
        <div className="rounded-md bg-warning/10 px-3 py-2.5 text-sm text-warning">
          This will permanently redact: <strong>{record.title}</strong>. The audit trail and
          blockchain proof are preserved, but sensitive content is replaced with [REDACTED].
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="erase-reason">Reason for Erasure</Label>
          <Textarea
            id="erase-reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Explain your erasure request"
          />
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="danger" onClick={() => mutation.mutate()} disabled={mutation.isPending || reason.length < 5}>
            {mutation.isPending ? "Erasing..." : "Confirm Erasure"}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}

/**
 * Register New Patient — Hospital Registration Staff (admin).
 *
 * Represents the hospital front desk creating a patient ACCOUNT + demographic
 * profile. It does NOT create clinical records — a doctor authors those in the
 * Provider Portal. Reuses the existing admin registration API
 * (POST /api/v1/patients/register); no new auth/model.
 */

import { useState, type FormEvent } from "react";
import { UserPlus, CheckCircle2, Hospital, AlertCircle } from "lucide-react";
import { adminService, type RegisteredPatient } from "@/services/adminService";
import { getErrorMessage } from "@/services/api";
import { useAuth } from "@/contexts/AuthContext";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { PageHero } from "@/components/shared/PageHero";
import { PROVIDER_ORG_NAME, humanize } from "@/lib/utils";

const BLOOD_GROUPS = ["", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];

// Roles each actor may create. Admin: any. Registration staff: no admin/dpo.
const ADMIN_ASSIGNABLE = ["patient", "doctor", "registration_staff", "admin", "dpo"];
const STAFF_ASSIGNABLE = ["patient", "doctor", "registration_staff"];

export function RegisterPatient() {
  const { user } = useAuth();
  const assignableRoles = user?.role === "admin" ? ADMIN_ASSIGNABLE : STAFF_ASSIGNABLE;

  const [role, setRole] = useState("patient");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [bloodGroup, setBloodGroup] = useState("");
  const [allergies, setAllergies] = useState("");
  const [chronic, setChronic] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState<RegisteredPatient | null>(null);

  const isPatient = role === "patient";

  const reset = () => {
    setFullName(""); setEmail(""); setPassword(""); setPhone("");
    setAddress(""); setBloodGroup(""); setAllergies(""); setChronic("");
  };

  const toList = (s: string) =>
    s.split(",").map((x) => x.trim()).filter(Boolean);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    setCreated(null);
    try {
      const result = await adminService.registerPatient({
        full_name: fullName.trim(),
        email: email.trim(),
        password,
        role,
        // demographics only meaningful for patients
        phone_number: isPatient && phone.trim() ? phone.trim() : undefined,
        address: isPatient && address.trim() ? address.trim() : undefined,
        blood_group: isPatient && bloodGroup ? bloodGroup : undefined,
        allergies: isPatient && allergies ? toList(allergies) : undefined,
        chronic_conditions: isPatient && chronic ? toList(chronic) : undefined,
      });
      setCreated(result);
      reset();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHero
        title="Register New User"
        subtitle={`${PROVIDER_ORG_NAME} — Hospital Registration Desk · create patient, doctor & staff accounts`}
        icon={Hospital}
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <UserPlus className="h-4 w-4 text-primary-600" />
              User Registration
            </CardTitle>
            <p className="text-xs text-neutral-500">
              Creates the account (and demographic profile for patients). Clinical
              records are authored separately by a doctor in the Provider Portal.
            </p>
          </CardHeader>
          <CardContent>
            {error && (
              <div className="mb-4 flex items-center gap-2 rounded-md bg-danger/5 px-3 py-2.5 text-sm text-danger">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                {error}
              </div>
            )}
            <form onSubmit={submit} className="space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="role">Account Role *</Label>
                  <select id="role" value={role} onChange={(e) => setRole(e.target.value)}
                    className="h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm">
                    {assignableRoles.map((r) => <option key={r} value={r}>{humanize(r)}</option>)}
                  </select>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="full_name">Full Name *</Label>
                  <Input id="full_name" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Rahul Kumar" required />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="email">Email *</Label>
                  <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="rahul@example.com" required />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="password">Initial Password *</Label>
                  <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Min 8 characters" required />
                </div>
                {isPatient && (
                  <>
                    <div className="space-y-1.5">
                      <Label htmlFor="phone">Phone</Label>
                      <Input id="phone" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+91-9xxxxxxxxx" />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="blood">Blood Group</Label>
                      <select id="blood" value={bloodGroup} onChange={(e) => setBloodGroup(e.target.value)}
                        className="h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm">
                        {BLOOD_GROUPS.map((b) => <option key={b} value={b}>{b || "— Select —"}</option>)}
                      </select>
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="allergies">Allergies (comma-separated)</Label>
                      <Input id="allergies" value={allergies} onChange={(e) => setAllergies(e.target.value)} placeholder="Penicillin, Sulfa drugs" />
                    </div>
                  </>
                )}
              </div>
              {isPatient && (
                <>
                  <div className="space-y-1.5">
                    <Label htmlFor="chronic">Chronic Conditions (comma-separated)</Label>
                    <Input id="chronic" value={chronic} onChange={(e) => setChronic(e.target.value)} placeholder="Hypertension, Diabetes" />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="address">Address</Label>
                    <Textarea id="address" value={address} onChange={(e) => setAddress(e.target.value)} placeholder="Street, City, State, PIN" />
                  </div>
                </>
              )}

              <Button type="submit" disabled={submitting || !fullName.trim() || !email.trim() || password.length < 8} className="gap-2">
                <UserPlus className="h-4 w-4" />
                {submitting ? "Creating account..." : `Register ${humanize(role)}`}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Confirmation */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Registration Result</CardTitle>
          </CardHeader>
          <CardContent>
            {created ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-success">
                  <CheckCircle2 className="h-5 w-5" />
                  <span className="font-semibold">{humanize(created.role)} account created</span>
                </div>
                <dl className="space-y-2 text-sm">
                  <Row label="Name" value={created.full_name} />
                  <Row label="Role" value={humanize(created.role)} />
                  {created.patient_id && <Row label="Patient ID" value={created.patient_id} mono />}
                  <Row label="Login" value={created.email} />
                  <Row label="Status" value={created.status} />
                </dl>
                <div className="rounded-md bg-neutral-50 px-3 py-2 text-xs text-neutral-500">
                  Share the login email with the patient. The password is set once
                  during registration and is never shown again (stored hashed).
                </div>
                <p className="text-xs text-neutral-500">
                  Next: a doctor opens the Provider Portal, searches this patient,
                  and creates clinical records.
                </p>
              </div>
            ) : (
              <p className="py-8 text-center text-sm text-neutral-400">
                Fill the form and submit to create a patient account.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-neutral-400">{label}</dt>
      <dd className={`text-neutral-800 ${mono ? "font-mono text-xs" : ""}`}>{value}</dd>
    </div>
  );
}

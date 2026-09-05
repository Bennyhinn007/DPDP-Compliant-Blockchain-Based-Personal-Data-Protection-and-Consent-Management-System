/**
 * Doctor Dashboard.
 *
 * Consent-gated patient record access with DPDP compliance visualization.
 */

import { useState } from "react";
import { motion } from "framer-motion";
import {
  Search,
  ShieldCheck,
  ShieldX,
  FileText,
  User,
  AlertTriangle,
  CheckCircle2,
  Clock,
} from "lucide-react";
import { doctorService, type PatientSearchResult, type PatientAccessResult } from "@/services/doctorService";
import { getErrorMessage } from "@/services/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { PageHero } from "@/components/shared/PageHero";
import { formatDateTime, humanize } from "@/lib/utils";

export function DoctorDashboard() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PatientSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [accessResult, setAccessResult] = useState<PatientAccessResult | null>(null);
  const [accessDenied, setAccessDenied] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    if (query.length < 2) return;
    setSearching(true);
    setAccessResult(null);
    setAccessDenied(null);
    try {
      const patients = await doctorService.searchPatients(query);
      setResults(patients);
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
  };

  const handleAccess = async (patientId: string) => {
    setLoading(true);
    setAccessResult(null);
    setAccessDenied(null);
    try {
      const result = await doctorService.getPatientRecords(patientId);
      setAccessResult(result);
    } catch (err: unknown) {
      const message = getErrorMessage(err);
      setAccessDenied(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHero
        title="Doctor Dashboard"
        subtitle="Consent-gated patient access — DPDP Act compliant"
        icon={ShieldCheck}
      />

      {/* Search */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Search className="h-4 w-4 text-primary-600" />
            Patient Search
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              placeholder="Search by patient name..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            />
            <Button onClick={handleSearch} disabled={searching || query.length < 2}>
              {searching ? "Searching..." : "Search"}
            </Button>
          </div>

          {results.length > 0 && (
            <div className="mt-4 space-y-2">
              {results.map((patient) => (
                <motion.div
                  key={patient._id}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-center justify-between rounded-lg border border-neutral-200 p-3"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary-50">
                      <User className="h-4 w-4 text-primary-600" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-neutral-800">{patient.full_name}</p>
                      <div className="flex items-center gap-1">
                        {patient.has_treatment_consent ? (
                          <Badge variant="success">
                            <ShieldCheck className="mr-1 h-3 w-3" />
                            Consent Active
                          </Badge>
                        ) : (
                          <Badge variant="danger">
                            <ShieldX className="mr-1 h-3 w-3" />
                            No Consent
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant={patient.has_treatment_consent ? "default" : "outline"}
                    onClick={() => handleAccess(patient._id)}
                    disabled={loading}
                  >
                    <FileText className="h-3.5 w-3.5" />
                    Access Records
                  </Button>
                </motion.div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Access Denied */}
      {accessDenied && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <Card className="border-danger/30">
            <CardContent className="flex items-start gap-4 p-6">
              <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-danger/10">
                <AlertTriangle className="h-6 w-6 text-danger" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-danger">Access Denied</h3>
                <p className="mt-1 text-sm text-neutral-600">{accessDenied}</p>
                <div className="mt-3 rounded-md bg-neutral-50 px-3 py-2 text-xs text-neutral-500">
                  <strong>DPDP Act Compliance:</strong> Data access requires explicit patient consent.
                  This denial has been recorded in the audit log.
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Access Granted — Records */}
      {accessResult && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
          {/* Access confirmation */}
          <Card className="border-success/30">
            <CardContent className="flex items-start gap-4 p-5">
              <CheckCircle2 className="h-6 w-6 flex-shrink-0 text-success" />
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-semibold text-success">Access Granted</h3>
                  <Badge variant="success">Consent Verified</Badge>
                </div>
                <p className="mt-1 text-sm text-neutral-600">
                  Patient: <strong>{accessResult.patient.full_name}</strong> ·
                  Blood Group: {accessResult.patient.blood_group || "N/A"} ·
                  Allergies: {accessResult.patient.allergies.join(", ") || "None"}
                </p>
                <p className="mt-1 text-xs text-neutral-400">
                  Consent granted: {formatDateTime(accessResult.consent.granted_at)} ·
                  Expires: {formatDateTime(accessResult.consent.expires_at)}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Records */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <FileText className="h-4 w-4 text-primary-600" />
                Healthcare Records ({accessResult.records.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {accessResult.records.map((rec, i) => (
                  <motion.div
                    key={rec._id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="rounded-lg border border-neutral-200 p-4"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-neutral-800">{rec.title}</span>
                        <Badge variant="neutral">{humanize(rec.record_type)}</Badge>
                      </div>
                      <div className="flex items-center gap-1 text-xs text-neutral-400">
                        <Clock className="h-3 w-3" />
                        {formatDateTime(rec.created_at)}
                      </div>
                    </div>
                    <p className="mt-2 text-sm text-neutral-600">{rec.description}</p>
                    {rec.treatment_notes && (
                      <p className="mt-1 text-xs text-neutral-500">
                        <strong>Treatment:</strong> {rec.treatment_notes}
                      </p>
                    )}
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
  );
}

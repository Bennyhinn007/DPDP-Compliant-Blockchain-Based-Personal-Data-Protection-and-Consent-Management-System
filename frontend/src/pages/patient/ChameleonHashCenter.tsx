/**
 * Chameleon Hash Visualization Center.
 *
 * Research contribution showcase: Traditional Hash vs Chameleon Hash.
 * Demonstrates how DPDP rights (correction, erasure) are compatible
 * with blockchain immutability through authorized hash collisions.
 */

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Hash,
  Link2,
  ShieldCheck,
  ShieldX,
  FileEdit,
  Trash2,
  ArrowRight,
  CheckCircle2,
  XCircle,
  Fingerprint,
  BookOpen,
  Sparkles,
  KeyRound,
} from "lucide-react";
import api from "@/services/api";
import { integrityService, type ChameleonDemoResult } from "@/services/integrityService";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageHero } from "@/components/shared/PageHero";
import { formatDateTime } from "@/lib/utils";

export function ChameleonHashCenter() {
  const { data: proofHistory = [] } = useQuery({
    queryKey: ["chameleon-proofs"],
    queryFn: async () => {
      try {
        const { data } = await api.get("/audit/timeline?action_type=update");
        return (data.timeline || []).filter(
          (e: { details?: { chameleon_proof?: string } }) => e.details?.chameleon_proof
        );
      } catch {
        return [];
      }
    },
  });

  return (
    <div className="space-y-8">
      {/* Header */}
      <PageHero
        title="Chameleon Hash Visualization Center"
        subtitle="Research contribution: Redactable blockchain architecture for DPDP compliance"
        icon={Fingerprint}
        pill={{ label: "Research", tone: "accent" }}
      />

      {/* Section 1: Traditional vs Chameleon Comparison */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Traditional Hash */}
        <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>
          <Card className="h-full border-danger/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base text-danger">
                <XCircle className="h-5 w-5" />
                Traditional Hashing
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <WorkflowStep
                icon={Hash}
                title="Record Created"
                description="SHA-256 hash computed and stored on blockchain"
                color="text-neutral-600"
              />
              <div className="flex justify-center">
                <ArrowRight className="h-4 w-4 text-neutral-300" />
              </div>
              <WorkflowStep
                icon={FileEdit}
                title="Record Modified (Correction)"
                description="New data produces different hash"
                color="text-warning"
              />
              <div className="flex justify-center">
                <ArrowRight className="h-4 w-4 text-neutral-300" />
              </div>
              <WorkflowStep
                icon={ShieldX}
                title="Chain Broken"
                description="Blockchain anchor no longer matches. Integrity violation detected."
                color="text-danger"
              />
              <div className="rounded-lg border border-danger/20 bg-danger/5 p-3">
                <p className="text-xs font-medium text-danger">Problem:</p>
                <p className="mt-1 text-xs text-neutral-600">
                  Traditional blockchains make DPDP compliance impossible.
                  The Right to Correction and Right to Erasure require data modification,
                  but any modification breaks the hash chain.
                </p>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Chameleon Hash */}
        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}>
          <Card className="h-full border-success/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base text-success">
                <CheckCircle2 className="h-5 w-5" />
                Chameleon Hashing (This System)
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <WorkflowStep
                icon={Hash}
                title="Record Created"
                description="SHA-256 hash computed and anchored on-chain"
                color="text-neutral-600"
              />
              <div className="flex justify-center">
                <ArrowRight className="h-4 w-4 text-neutral-300" />
              </div>
              <WorkflowStep
                icon={FileEdit}
                title="Authorized Modification"
                description="Correction approved by authorized party with legal basis"
                color="text-primary-600"
              />
              <div className="flex justify-center">
                <ArrowRight className="h-4 w-4 text-neutral-300" />
              </div>
              <WorkflowStep
                icon={ShieldCheck}
                title="Chain Preserved"
                description="Redaction proof links old hash → new hash. Verification system accepts the modification."
                color="text-success"
              />
              <div className="rounded-lg border border-success/20 bg-success/5 p-3">
                <p className="text-xs font-medium text-success">Solution:</p>
                <p className="mt-1 text-xs text-neutral-600">
                  Chameleon hashing enables authorized modifications while preserving
                  blockchain verification. The proof chain proves the modification was lawful.
                </p>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Section 2: Formula */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Fingerprint className="h-5 w-5 text-primary-600" />
            Mathematical Foundation
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg bg-neutral-50 p-6 text-center">
            <p className="font-mono text-lg font-semibold text-neutral-800">
              CH(m, r) = g<sup>m</sup> · y<sup>r</sup> mod p
            </p>
            <div className="mt-4 grid grid-cols-2 gap-4 text-left sm:grid-cols-4">
              <div className="rounded-md bg-white p-2 shadow-sm">
                <span className="font-mono text-xs font-bold text-primary-600">m</span>
                <p className="text-xs text-neutral-500">Message (record hash)</p>
              </div>
              <div className="rounded-md bg-white p-2 shadow-sm">
                <span className="font-mono text-xs font-bold text-primary-600">r</span>
                <p className="text-xs text-neutral-500">Randomness value</p>
              </div>
              <div className="rounded-md bg-white p-2 shadow-sm">
                <span className="font-mono text-xs font-bold text-primary-600">y</span>
                <p className="text-xs text-neutral-500">Public key</p>
              </div>
              <div className="rounded-md bg-white p-2 shadow-sm">
                <span className="font-mono text-xs font-bold text-primary-600">p</span>
                <p className="text-xs text-neutral-500">Prime modulus</p>
              </div>
            </div>
            <p className="mt-4 text-xs text-neutral-500">
              With trapdoor key <span className="font-mono font-bold">x</span>, compute new randomness
              <span className="font-mono font-bold"> r&apos;</span> such that
              <span className="font-mono"> CH(m, r) = CH(m&apos;, r&apos;)</span>
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Section 2.5: LIVE COLLISION DEMO */}
      <LiveCollisionDemo />

      {/* Section 3 & 4: DPDP Workflows */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Right to Correction */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <FileEdit className="h-5 w-5 text-primary-600" />
              DPDP Right to Correction
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="space-y-3">
              {[
                { step: "Patient submits correction request", badge: "Patient" },
                { step: "System verifies identity (JWT + session)", badge: "Auth" },
                { step: "Authorization granted (DPDP Section 12)", badge: "Legal" },
                { step: "Previous version archived", badge: "Archive" },
                { step: "Correction applied to record", badge: "Update" },
                { step: "Chameleon proof generated", badge: "Proof" },
                { step: "New blockchain anchor created", badge: "Chain" },
                { step: "Audit trail preserved", badge: "Audit" },
              ].map((item, i) => (
                <motion.li
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="flex items-center gap-3"
                >
                  <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-primary-100 text-xs font-bold text-primary-700">
                    {i + 1}
                  </span>
                  <span className="flex-1 text-sm text-neutral-700">{item.step}</span>
                  <Badge variant="neutral">{item.badge}</Badge>
                </motion.li>
              ))}
            </ol>
          </CardContent>
        </Card>

        {/* Right to Erasure */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Trash2 className="h-5 w-5 text-danger" />
              DPDP Right to Erasure
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="space-y-3">
              {[
                { step: "Patient requests data erasure", badge: "Patient" },
                { step: "Identity verification (MFA-ready)", badge: "Auth" },
                { step: "Legal basis confirmed (Section 12)", badge: "Legal" },
                { step: "Previous version archived (encrypted)", badge: "Archive" },
                { step: "Sensitive fields → [REDACTED]", badge: "Redact" },
                { step: "Chameleon proof links old → new hash", badge: "Proof" },
                { step: "Blockchain anchor updated", badge: "Chain" },
                { step: "Audit trail preserved (content erased)", badge: "Audit" },
              ].map((item, i) => (
                <motion.li
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="flex items-center gap-3"
                >
                  <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-danger/10 text-xs font-bold text-danger">
                    {i + 1}
                  </span>
                  <span className="flex-1 text-sm text-neutral-700">{item.step}</span>
                  <Badge variant="neutral">{item.badge}</Badge>
                </motion.li>
              ))}
            </ol>
          </CardContent>
        </Card>
      </div>

      {/* Section 5: Proof History */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Link2 className="h-5 w-5 text-primary-600" />
            Chameleon Hash Proof History
          </CardTitle>
        </CardHeader>
        <CardContent>
          {proofHistory.length === 0 ? (
            <p className="py-8 text-center text-sm text-neutral-400">
              No chameleon hash proofs generated yet. Perform a record correction or erasure to see proof history.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-neutral-200 text-left">
                    <th className="pb-2 pr-4 font-medium text-neutral-500">Type</th>
                    <th className="pb-2 pr-4 font-medium text-neutral-500">Reason</th>
                    <th className="pb-2 pr-4 font-medium text-neutral-500">Proof Hash</th>
                    <th className="pb-2 font-medium text-neutral-500">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {proofHistory.map((event: { _id: string; action_type: string; reason: string; details?: { chameleon_proof?: string }; created_at: string }) => (
                    <tr key={event._id} className="border-b border-neutral-100">
                      <td className="py-2.5 pr-4">
                        <Badge variant={event.action_type === "delete" ? "danger" : "default"}>
                          {event.action_type === "delete" ? "Erasure" : "Correction"}
                        </Badge>
                      </td>
                      <td className="py-2.5 pr-4 text-neutral-700">{event.reason}</td>
                      <td className="py-2.5 pr-4 font-mono text-xs text-neutral-500">
                        {event.details?.chameleon_proof?.slice(0, 16)}...
                      </td>
                      <td className="py-2.5 text-neutral-400">{formatDateTime(event.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Section 6: Research Value */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <BookOpen className="h-5 w-5 text-secondary" />
            Research Contribution
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-neutral-200 p-4">
              <h4 className="text-sm font-semibold text-neutral-800">Problem Statement</h4>
              <p className="mt-2 text-xs text-neutral-600">
                Traditional blockchains enforce absolute immutability. India&apos;s DPDP Act (2023) grants
                citizens the right to correct and erase personal data. These requirements conflict
                directly with blockchain architecture.
              </p>
            </div>
            <div className="rounded-lg border border-neutral-200 p-4">
              <h4 className="text-sm font-semibold text-neutral-800">Proposed Solution</h4>
              <p className="mt-2 text-xs text-neutral-600">
                Chameleon Hash functions allow authorized parties (holding a trapdoor key) to find
                hash collisions. This enables data modification while maintaining the same hash output,
                preserving blockchain chain validity.
              </p>
            </div>
            <div className="rounded-lg border border-neutral-200 p-4">
              <h4 className="text-sm font-semibold text-neutral-800">Key Innovation</h4>
              <p className="mt-2 text-xs text-neutral-600">
                This system combines: (1) SHA-256 verification hashes for integrity detection,
                (2) Chameleon hash proof chains for authorized modifications, (3) Blockchain anchoring
                for immutable audit trails — achieving DPDP compliance without sacrificing verification.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function WorkflowStep({
  icon: Icon,
  title,
  description,
  color,
}: {
  icon: typeof Hash;
  title: string;
  description: string;
  color: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <div className={`mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-neutral-100 ${color}`}>
        <Icon className="h-4 w-4" />
      </div>
      <div>
        <p className="text-sm font-medium text-neutral-800">{title}</p>
        <p className="text-xs text-neutral-500">{description}</p>
      </div>
    </div>
  );
}


// ─────────────────────────────────────────────────────────────────────
// LIVE CHAMELEON COLLISION DEMO
// ─────────────────────────────────────────────────────────────────────

function LiveCollisionDemo() {
  const [original, setOriginal] = useState("Diagnosis: I25.1 (Atherosclerotic heart disease)");
  const [modified, setModified] = useState("Diagnosis: I25.10 (corrected under DPDP Section 12)");
  const [result, setResult] = useState<ChameleonDemoResult | null>(null);

  const mutation = useMutation({
    mutationFn: () => integrityService.chameleonCollisionDemo(original, modified),
    onSuccess: (data) => setResult(data),
  });

  return (
    <Card className="border-primary-200">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Sparkles className="h-5 w-5 text-primary-600" />
          Live Chameleon Collision — Try It Yourself
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-neutral-600">
          Enter any two different messages. The system generates a <strong>real cryptographic
          trapdoor collision</strong> so that both messages produce the <strong>identical</strong> chameleon
          hash — proving how a record can be lawfully redacted without breaking its blockchain anchor.
        </p>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="orig">Original Content</Label>
            <Input id="orig" value={original} onChange={(e) => setOriginal(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="mod">Corrected / Redacted Content</Label>
            <Input id="mod" value={modified} onChange={(e) => setModified(e.target.value)} />
          </div>
        </div>

        <Button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending || !original || !modified || original === modified}
          className="gap-2"
        >
          <Sparkles className="h-4 w-4" />
          {mutation.isPending ? "Computing collision..." : "Generate Real Collision"}
        </Button>

        {result && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-3 rounded-lg border border-neutral-200 bg-neutral-50 p-4"
          >
            {/* Verdict */}
            <div
              className={`flex items-center gap-2 rounded-md px-3 py-2.5 text-sm font-medium ${
                result.hash_identical ? "bg-success/10 text-success" : "bg-danger/10 text-danger"
              }`}
            >
              {result.hash_identical ? (
                <CheckCircle2 className="h-4 w-4" />
              ) : (
                <XCircle className="h-4 w-4" />
              )}
              {result.hash_identical
                ? "Content changed, but the chameleon hash is IDENTICAL — collision verified."
                : "Verification failed."}
            </div>

            {/* Scheme */}
            <div className="flex items-center gap-2 text-xs text-neutral-500">
              <KeyRound className="h-3.5 w-3.5" />
              <span className="font-mono">{result.proof.scheme}</span>
              <Badge variant="neutral">{result.proof.modulus_bits}-bit</Badge>
            </div>

            {/* The identical hash */}
            <ProofRow label="Chameleon Hash (before AND after)" value={result.proof.chameleon_hash} highlight />
            <ProofRow label="Randomness r (original)" value={result.proof.original_r} />
            <ProofRow label="Randomness r' (trapdoor collision)" value={result.proof.collision_r} />
            <ProofRow label="Public Key y = g^x mod p" value={result.proof.public_key_y} />

            <div className="rounded-md bg-primary-50 px-3 py-2 text-xs text-primary-700">
              Both messages hash to the same value because the trapdoor holder computed a new
              randomness <span className="font-mono">r&apos;</span> satisfying{" "}
              <span className="font-mono">g^m · y^r = g^m&apos; · y^r&apos; (mod p)</span>. Without the
              secret key, this is computationally infeasible.
            </div>
          </motion.div>
        )}
      </CardContent>
    </Card>
  );
}

function ProofRow({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className={`rounded-md p-2.5 ${highlight ? "bg-success/5 border border-success/20" : "bg-white"}`}>
      <p className="text-[10px] font-medium uppercase tracking-wide text-neutral-400">{label}</p>
      <p className="mt-0.5 break-all font-mono text-xs text-neutral-700">
        {value.length > 90 ? `${value.slice(0, 90)}...` : value}
      </p>
    </div>
  );
}

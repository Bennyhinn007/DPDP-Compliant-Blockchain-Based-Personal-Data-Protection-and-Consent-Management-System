/**
 * Live Tamper-Attempt Demo.
 *
 * The project's thesis, shown side by side and live:
 *   - Editing a record directly breaks a traditional SHA-256 anchor
 *     (INTEGRITY_VIOLATION, red).
 *   - The same edit through the chameleon-hash trapdoor keeps the anchor
 *     valid via a real discrete-log collision (VERIFIED_MODIFIED, green).
 *
 * Safe and self-contained — it never touches real records.
 */

import { useState } from "react";
import { motion } from "framer-motion";
import { ShieldX, ShieldCheck, Play, AlertTriangle } from "lucide-react";
import { integrityService, type TamperDemoResult } from "@/services/integrityService";
import { getErrorMessage } from "@/services/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { truncateHash } from "@/lib/utils";

const DEFAULT_ORIGINAL = "Blood Pressure: 120/80, Diagnosis: Hypertension";
const DEFAULT_MODIFIED = "Blood Pressure: 118/76, Diagnosis: Hypertension (corrected)";

export function TamperDemo() {
  const [original, setOriginal] = useState(DEFAULT_ORIGINAL);
  const [modified, setModified] = useState(DEFAULT_MODIFIED);
  const [result, setResult] = useState<TamperDemoResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const run = async () => {
    setError("");
    setLoading(true);
    try {
      setResult(await integrityService.tamperDemo(original, modified));
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-warning" />
          Live Tamper-Attempt Demo
        </CardTitle>
        <p className="mt-1 text-sm text-neutral-500">
          Watch the same edit break a traditional hash but survive a chameleon-hash correction.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="orig">Original record content</Label>
            <Textarea id="orig" rows={3} value={original} onChange={(e) => setOriginal(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="mod">Edited content</Label>
            <Textarea id="mod" rows={3} value={modified} onChange={(e) => setModified(e.target.value)} />
          </div>
        </div>

        {error && (
          <div className="rounded-md bg-danger/5 px-3 py-2 text-sm text-danger">{error}</div>
        )}

        <Button onClick={run} disabled={loading || original.trim().length < 3}>
          <Play className="h-4 w-4" />
          {loading ? "Running..." : "Run tamper attempt"}
        </Button>

        {result && (
          <div className="grid gap-4 md:grid-cols-2">
            {/* A — Unauthorized tamper */}
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="rounded-xl border border-danger/30 bg-danger/5 p-4"
            >
              <div className="flex items-center gap-2 text-danger">
                <ShieldX className="h-5 w-5" />
                <span className="text-sm font-semibold">{result.tamper.title}</span>
              </div>
              <p className="mt-2 text-sm text-neutral-600">{result.tamper.message}</p>
              <div className="mt-3 space-y-1 font-mono text-[11px] text-neutral-600">
                <div>anchor  = {truncateHash(result.tamper.anchor_hash, 10)}</div>
                <div>current = {truncateHash(result.tamper.current_hash, 10)}</div>
                <div className="text-danger">match = {String(result.tamper.hashes_match)}</div>
              </div>
              <div className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-danger/10 px-3 py-1 text-xs font-semibold text-danger ring-1 ring-danger/20">
                {result.tamper.status}
              </div>
            </motion.div>

            {/* B — Lawful chameleon correction */}
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: 0.1 }}
              className="rounded-xl border border-success/30 bg-success/5 p-4"
            >
              <div className="flex items-center gap-2 text-success">
                <ShieldCheck className="h-5 w-5" />
                <span className="text-sm font-semibold">{result.lawful.title}</span>
              </div>
              <p className="mt-2 text-sm text-neutral-600">{result.lawful.message}</p>
              <div className="mt-3 space-y-1 font-mono text-[11px] text-neutral-600">
                <div>CH  = {truncateHash(result.lawful.chameleon_hash, 10)}</div>
                <div>r   = {truncateHash(result.lawful.original_r, 8)}</div>
                <div>r'  = {truncateHash(result.lawful.collision_r, 8)}</div>
                <div className="text-success">
                  hash identical after edit = {String(result.lawful.hash_identical_after_edit)}
                </div>
              </div>
              <div className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-success/10 px-3 py-1 text-xs font-semibold text-success ring-1 ring-success/20">
                {result.lawful.status}
              </div>
              <p className="mt-3 font-mono text-[10px] text-neutral-400">{result.lawful.formula}</p>
            </motion.div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

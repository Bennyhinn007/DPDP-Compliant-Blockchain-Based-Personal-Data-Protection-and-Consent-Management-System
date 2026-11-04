/**
 * Fingerprint (SecuGen) Panel - admin enroll / verify / remove.
 *
 * Prototype: capture and matching run on this PC through the SecuGen local
 * service; the server trusts the reported score. Re-enrolling or removing needs a
 * recent physical-presence proof (a successful "Verify now" or an RFID tap), which
 * stays valid for only about 25 seconds.
 */
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Fingerprint, CheckCircle2, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { biometricService, presenceRequired } from "@/services/biometricService";
import { getErrorMessage } from "@/services/api";
import { FingerprintError, secugenProvider, type CaptureResult } from "@/lib/fingerprint";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

// SecuGen's recommended strong-match level (of 199). Stricter than the server's
// default of 80 because two same-day scans of one finger should match well.
const ENROLL_CONFIRM_MIN_SCORE = 100;

const PRESENCE_HINT =
  "Verify your fingerprint (Verify now) or tap your RFID card first, then try again right away.";

export function FingerprintPanel() {
  const queryClient = useQueryClient();
  const { data: status, isLoading } = useQuery({
    queryKey: ["biometric-status"],
    queryFn: biometricService.status,
  });

  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<string | undefined>(undefined);
  const [quality, setQuality] = useState<number | null>(null);

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["biometric-status"] });

  const fail = (err: unknown) => {
    if (presenceRequired(err)) setError(PRESENCE_HINT);
    else if (err instanceof FingerprintError) setError(err.message);
    else setError(getErrorMessage(err));
  };

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await fn();
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  };

  const handleEnroll = () =>
    run(async () => {
      setMessage("Place finger on the reader...");
      const first: CaptureResult = await secugenProvider.capture();
      setMessage("Place the same finger again...");
      const second: CaptureResult = await secugenProvider.capture();
      const score = await secugenProvider.match(first.template, second.template);
      if (score < ENROLL_CONFIRM_MIN_SCORE) {
        throw new FingerprintError("The two scans did not match, try again");
      }
      const best = Math.max(first.quality, second.quality);
      await biometricService.enroll(first.template, "secugen", best);
      setQuality(best);
      setPreview(first.previewBmpBase64);
      setMessage(`Fingerprint enrolled (quality ${best}).`);
      toast.success("Fingerprint enrolled");
      refresh();
    });

  const handleVerify = () =>
    run(async () => {
      setMessage("Place finger on the reader...");
      const live = await secugenProvider.capture();
      const enrolled = await biometricService.getTemplate();
      const score = await secugenProvider.match(enrolled.template, live.template);
      const result = await biometricService.verify(score, "secugen");
      setPreview(live.previewBmpBase64);
      setQuality(live.quality);
      if (result.verified) {
        setMessage("Fingerprint verified. Physical presence is valid for about 25 seconds.");
      }
    });

  const handleRemove = () =>
    run(async () => {
      await biometricService.remove();
      setPreview(undefined);
      setQuality(null);
      setMessage("Fingerprint enrollment removed.");
      toast.success("Fingerprint removed");
      refresh();
    });

  const enrolled = !!status?.enrolled;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Fingerprint className="h-4 w-4 text-success" />
          Fingerprint (SecuGen)
          {!isLoading && (
            <Badge variant={enrolled ? "success" : "neutral"}>
              {enrolled ? "Enrolled" : "Not enrolled"}
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {enrolled && (
          <p className="text-sm text-neutral-600">
            Provider: {status?.provider ?? "secugen"}
            {status?.quality != null && ` · Quality: ${status.quality}`}
            {status?.enrolled_at && ` · Enrolled: ${new Date(status.enrolled_at).toLocaleString()}`}
          </p>
        )}

        <div className="flex flex-wrap gap-2">
          <Button type="button" onClick={handleEnroll} disabled={busy}>
            {enrolled ? "Re-enroll fingerprint" : "Enroll fingerprint"}
          </Button>
          {enrolled && (
            <>
              <Button type="button" variant="outline" onClick={handleVerify} disabled={busy}>
                Verify now
              </Button>
              <Button type="button" variant="outline" onClick={handleRemove} disabled={busy}>
                Remove
              </Button>
            </>
          )}
        </div>

        <div aria-live="polite" className="space-y-2">
          {message && (
            <p className="flex items-center gap-2 text-sm text-neutral-700">
              <CheckCircle2 className="h-4 w-4 text-success" />
              {message}
            </p>
          )}
          {error && (
            <p className="flex items-center gap-2 text-sm text-danger">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              {error}
            </p>
          )}
          {quality !== null && <p className="text-xs text-neutral-500">Scan quality: {quality}</p>}
          {preview && (
            <img
              src={`data:image/bmp;base64,${preview}`}
              alt="Fingerprint scan preview"
              className="h-32 w-32 rounded border border-neutral-200 object-contain"
            />
          )}
        </div>

        <p className="text-xs text-neutral-500">
          Matching runs on this PC via the SecuGen service; the server trusts the reported score
          (prototype). Re-enrolling or removing needs a successful Verify now (or an RFID tap)
          within about 25 seconds.
        </p>
      </CardContent>
    </Card>
  );
}

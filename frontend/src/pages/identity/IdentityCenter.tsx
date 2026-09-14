/**
 * Identity Center — SIH 26125 (ADDITIVE).
 *
 * Lets a signed-in user create a decentralized identity (DID) linked to their
 * existing account, view the DID document, and run a cryptographic
 * challenge-response self-verification. The private key is generated and stored
 * CLIENT-SIDE (prototype custody) and never sent to the server.
 *
 * This is an additional identity layer — it does not replace the existing login.
 */

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, ShieldCheck, ShieldX, Copy, Check, Fingerprint, AlertTriangle } from "lucide-react";
import { PageHero } from "@/components/shared/PageHero";
import { PageLoader } from "@/components/shared/PageLoader";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { identityService } from "@/services/identityService";
import { generateWallet, saveWallet, loadWallet, personalSign, type Wallet } from "@/lib/wallet";
import { getErrorMessage } from "@/services/api";
import { truncateHash } from "@/lib/utils";

export function IdentityCenter() {
  const queryClient = useQueryClient();
  const [wallet, setWallet] = useState<Wallet | null>(loadWallet());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [copied, setCopied] = useState(false);
  const [verifyResult, setVerifyResult] = useState<null | boolean>(null);

  const { data: did, isLoading } = useQuery({
    queryKey: ["my-did"],
    queryFn: identityService.myDid,
  });

  const createDid = async () => {
    setError("");
    setMsg("");
    setBusy(true);
    try {
      // Generate a client-side keypair (private key never leaves the browser).
      const w = wallet ?? generateWallet();
      saveWallet(w);
      setWallet(w);
      await identityService.createDid(w.publicKey);
      setMsg("DID created and linked to your account.");
      queryClient.invalidateQueries({ queryKey: ["my-did"] });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  // Cryptographic self-test: challenge → sign (client) → verify (server).
  const runSelfVerify = async () => {
    setError("");
    setVerifyResult(null);
    setBusy(true);
    try {
      const w = loadWallet();
      if (!w || !did) throw new Error("Create a DID first");
      const challenge = await identityService.challenge(did.did);
      const signature = await personalSign(challenge.message, w.privateKey);
      // Verify issues a JWT; here we only confirm the signature is accepted.
      await identityService.verify(did.did, challenge.nonce, signature);
      setVerifyResult(true);
      setMsg("Cryptographic identity verified — signature accepted by the server.");
    } catch (err) {
      setVerifyResult(false);
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const copyDid = () => {
    if (!did) return;
    navigator.clipboard.writeText(did.did);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  if (isLoading) return <PageLoader message="Loading identity..." />;

  return (
    <div className="space-y-6">
      <PageHero
        title="Identity Center"
        subtitle="Your decentralized identity (DID) — an additional cryptographic identity layer"
        icon={KeyRound}
        pill={did ? { label: did.status === "active" ? "DID Active" : did.status, tone: did.status === "active" ? "success" : "warning" } : undefined}
      />

      {/* Prototype disclosure */}
      <div className="flex items-start gap-2 rounded-lg border border-warning/30 bg-warning/5 px-4 py-3 text-sm text-warning">
        <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
        <span>
          <b>Prototype:</b> <code>did:rakshaid</code> is a project-specific DID method for
          demonstration (not an interoperable production DID network). The private key is
          held in your browser (prototype custody), never sent to the server.
        </span>
      </div>

      {error && <div className="rounded-md bg-danger/5 px-4 py-2.5 text-sm text-danger">{error}</div>}
      {msg && <div className="rounded-md bg-success/10 px-4 py-2.5 text-sm text-success">{msg}</div>}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* DID status / creation */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Fingerprint className="h-5 w-5 text-primary-600" />
              Decentralized Identity
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {did ? (
              <>
                <div>
                  <p className="text-xs font-medium text-neutral-500">DID</p>
                  <div className="mt-1 flex items-center gap-2">
                    <code className="break-all text-sm text-neutral-800">{did.did}</code>
                    <button onClick={copyDid} className="text-neutral-400 hover:text-primary-600" aria-label="Copy DID">
                      {copied ? <Check className="h-4 w-4 text-success" /> : <Copy className="h-4 w-4" />}
                    </button>
                  </div>
                </div>
                <div>
                  <p className="text-xs font-medium text-neutral-500">Address</p>
                  <code className="text-sm text-neutral-700">{did.address}</code>
                </div>
                <div>
                  <p className="text-xs font-medium text-neutral-500">DID hash (on-chain, bytes32)</p>
                  <code className="font-mono text-xs text-neutral-600">{truncateHash(did.did_hash, 12)}</code>
                </div>
                <Badge variant={did.status === "active" ? "success" : "warning"}>{did.status}</Badge>
              </>
            ) : (
              <>
                <p className="text-sm text-neutral-600">
                  You don't have a DID yet. Create one to add a cryptographically verifiable
                  identity on top of your existing account.
                </p>
                <Button onClick={createDid} disabled={busy}>
                  <KeyRound className="h-4 w-4" />
                  {busy ? "Creating..." : "Create My DID"}
                </Button>
              </>
            )}
          </CardContent>
        </Card>

        {/* Cryptographic verification */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-primary-600" />
              Cryptographic Identity Proof
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-neutral-600">
              Prove possession of your private key via an EIP-191 challenge-response:
              the server issues a one-time nonce, your browser signs it, and the server
              verifies the signature against your registered public key.
            </p>
            <Button variant="outline" onClick={runSelfVerify} disabled={busy || !did}>
              <ShieldCheck className="h-4 w-4" />
              {busy ? "Verifying..." : "Verify My Identity"}
            </Button>
            {verifyResult === true && (
              <div className="flex items-center gap-2 text-sm font-medium text-success">
                <ShieldCheck className="h-4 w-4" /> Signature verified by the server
              </div>
            )}
            {verifyResult === false && (
              <div className="flex items-center gap-2 text-sm font-medium text-danger">
                <ShieldX className="h-4 w-4" /> Verification failed
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {did?.did_document !== undefined && (
        <Card>
          <CardHeader>
            <CardTitle>DID Document</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="overflow-x-auto rounded-lg bg-neutral-50 p-4 text-xs text-neutral-700">
              {JSON.stringify(did?.did_document ?? {}, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

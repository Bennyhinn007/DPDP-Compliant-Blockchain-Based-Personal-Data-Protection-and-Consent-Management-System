/**
 * Digital Asset Center — SIH 26125 Phase 3 (ADDITIVE).
 *
 * Register digital/organizational assets (encrypted metadata off-chain), mint
 * them as ERC-721 NFTs to a DID, and verify ownership. This is a SEPARATE asset
 * domain — patient healthcare records are never minted here.
 *
 * Chain-dependent actions (mint/verify) degrade gracefully when the chain is down.
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Boxes, Plus, ShieldCheck, AlertTriangle, BadgeCheck, XCircle } from "lucide-react";
import { PageHero } from "@/components/shared/PageHero";
import { PageLoader } from "@/components/shared/PageLoader";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { assetService, type NftVerification } from "@/services/assetService";
import { getErrorMessage } from "@/services/api";
import { truncateHash } from "@/lib/utils";

export function DigitalAssetCenter() {
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [form, setForm] = useState({ asset_type: "medical_device", name: "", description: "", spec: "" });
  const [mintTarget, setMintTarget] = useState<{ assetId: string; did: string }>({ assetId: "", did: "" });
  const [verifyId, setVerifyId] = useState("");
  const [verifyResult, setVerifyResult] = useState<NftVerification | null>(null);

  const { data: types = [] } = useQuery({ queryKey: ["asset-types"], queryFn: assetService.assetTypes });
  const { data: assets = [], isLoading } = useQuery({ queryKey: ["assets"], queryFn: assetService.listAssets });
  const { data: nfts = [] } = useQuery({ queryKey: ["nfts"], queryFn: () => assetService.listNfts() });

  const registerMut = useMutation({
    mutationFn: () => assetService.registerAsset(form.asset_type, {
      name: form.name, description: form.description, spec: form.spec,
    }),
    onSuccess: () => {
      setMsg("Asset registered (metadata encrypted off-chain).");
      setForm({ ...form, name: "", description: "", spec: "" });
      queryClient.invalidateQueries({ queryKey: ["assets"] });
    },
    onError: (e) => setError(getErrorMessage(e)),
  });

  const mintMut = useMutation({
    mutationFn: () => assetService.mint(mintTarget.assetId, mintTarget.did),
    onSuccess: (r) => {
      setMsg(`Minted NFT #${r.token_id}.`);
      setMintTarget({ assetId: "", did: "" });
      queryClient.invalidateQueries({ queryKey: ["nfts"] });
    },
    onError: (e) => setError(getErrorMessage(e)),
  });

  const doVerify = async () => {
    setError("");
    setVerifyResult(null);
    try {
      setVerifyResult(await assetService.verify(Number(verifyId)));
    } catch (e) {
      setError(getErrorMessage(e));
    }
  };

  if (isLoading) return <PageLoader message="Loading assets..." />;

  return (
    <div className="space-y-6">
      <PageHero
        title="Digital Asset Center"
        subtitle="Register digital assets, mint ownership NFTs to identities, verify ownership"
        icon={Boxes}
        pill={{ label: "NFT / ERC-721", tone: "primary" }}
      />

      <div className="flex items-start gap-2 rounded-lg border border-warning/30 bg-warning/5 px-4 py-3 text-sm text-warning">
        <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
        <span>
          Digital assets are a <b>separate domain</b> from patient healthcare records —
          records are never minted as NFTs. Minting requires a live blockchain and admin role.
        </span>
      </div>

      {error && <div className="rounded-md bg-danger/5 px-4 py-2.5 text-sm text-danger">{error}</div>}
      {msg && <div className="rounded-md bg-success/10 px-4 py-2.5 text-sm text-success">{msg}</div>}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Register asset */}
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Plus className="h-5 w-5 text-primary-600" />Register Asset</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="atype">Asset type</Label>
              <select id="atype" className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm"
                value={form.asset_type} onChange={(e) => setForm({ ...form, asset_type: e.target.value })}>
                {types.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
              </select>
            </div>
            <div className="space-y-1.5"><Label htmlFor="aname">Name</Label>
              <Input id="aname" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Radar Subsystem RX-9" /></div>
            <div className="space-y-1.5"><Label htmlFor="adesc">Description</Label>
              <Input id="adesc" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Secure communication module" /></div>
            <div className="space-y-1.5"><Label htmlFor="aspec">Spec</Label>
              <Input id="aspec" value={form.spec} onChange={(e) => setForm({ ...form, spec: e.target.value })} placeholder="X-band, v2.1" /></div>
            <Button onClick={() => registerMut.mutate()} disabled={registerMut.isPending || form.name.trim().length < 2}>
              <Plus className="h-4 w-4" />{registerMut.isPending ? "Registering..." : "Register Asset"}
            </Button>
          </CardContent>
        </Card>

        {/* Mint NFT */}
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><ShieldCheck className="h-5 w-5 text-primary-600" />Mint NFT to DID</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="masset">Asset</Label>
              <select id="masset" className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm"
                value={mintTarget.assetId} onChange={(e) => setMintTarget({ ...mintTarget, assetId: e.target.value })}>
                <option value="">Select an asset…</option>
                {assets.map((a) => <option key={a._id} value={a._id}>{a.name} ({a.asset_type})</option>)}
              </select>
            </div>
            <div className="space-y-1.5"><Label htmlFor="mdid">Owner DID</Label>
              <Input id="mdid" value={mintTarget.did} onChange={(e) => setMintTarget({ ...mintTarget, did: e.target.value })} placeholder="did:rakshaid:..." /></div>
            <Button onClick={() => mintMut.mutate()} disabled={mintMut.isPending || !mintTarget.assetId || !mintTarget.did}>
              <ShieldCheck className="h-4 w-4" />{mintMut.isPending ? "Minting..." : "Mint NFT"}
            </Button>
            <p className="text-xs text-neutral-400">Fails closed (503) if the blockchain is unavailable.</p>
          </CardContent>
        </Card>
      </div>

      {/* Registered assets */}
      <Card>
        <CardHeader><CardTitle>Registered Assets ({assets.length})</CardTitle></CardHeader>
        <CardContent>
          {assets.length === 0 ? <p className="py-4 text-center text-sm text-neutral-400">No assets yet.</p> : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {assets.map((a) => (
                <div key={a._id} className="rounded-lg border border-neutral-200 p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-neutral-800">{a.name}</span>
                    <Badge variant="secondary">{a.asset_type}</Badge>
                  </div>
                  <p className="mt-1 text-xs text-neutral-500">{a.description}</p>
                  <p className="mt-2 font-mono text-[10px] text-neutral-400">hash {truncateHash(a.metadata_hash, 8)}</p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Minted NFTs + verify */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Minted NFTs ({nfts.length})</CardTitle></CardHeader>
          <CardContent>
            {nfts.length === 0 ? <p className="py-4 text-center text-sm text-neutral-400">No NFTs minted yet.</p> : (
              <ul className="space-y-2">
                {nfts.map((n) => (
                  <li key={n._id} className="flex items-center justify-between rounded-md border border-neutral-200 px-3 py-2 text-sm">
                    <span>#{n.token_id ?? "?"} → <code className="text-xs">{truncateHash(n.owner_did, 8)}</code></span>
                    <Badge variant={n.status === "active" ? "success" : "warning"}>{n.status}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><BadgeCheck className="h-5 w-5 text-primary-600" />Verify Ownership</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="flex gap-2">
              <Input value={verifyId} onChange={(e) => setVerifyId(e.target.value)} placeholder="Token ID" type="number" />
              <Button variant="outline" onClick={doVerify} disabled={!verifyId}>Verify</Button>
            </div>
            {verifyResult && (
              <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-3 text-xs">
                {verifyResult.chain_available ? (
                  <div className="flex items-center gap-2 font-medium">
                    {verifyResult.verified
                      ? <span className="flex items-center gap-1 text-success"><BadgeCheck className="h-4 w-4" />Ownership verified on-chain</span>
                      : <span className="flex items-center gap-1 text-danger"><XCircle className="h-4 w-4" />Verification mismatch</span>}
                  </div>
                ) : (
                  <span className="text-warning">Chain unavailable — showing cached record only.</span>
                )}
                <div className="mt-2 space-y-1 font-mono text-neutral-600">
                  <div>owner DID: {truncateHash(verifyResult.owner_did || "", 8)}</div>
                  <div>metadata hash match: {String(verifyResult.metadata_hash_match ?? "n/a")}</div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

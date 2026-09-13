# SIH 26125 — Frontend Additions

> Existing pages, dashboards, navigation, and healthcare UI remain **UNCHANGED**.
> New pages are added and reuse the existing AppShell, UI components, and
> TanStack Query patterns. No redesign of the existing frontend.

## New pages

| Page | Route | Roles | Contents |
|---|---|---|---|
| **Identity Center** | `/identity` | all authenticated | Create DID, view DID Document, client-side key management (wallet), challenge-sign login, identity status + revocation |
| **Digital Asset Center** | `/assets` | admin / manager / user | Register asset, mint NFT, assign, controlled transfer, ownership verification, asset history |
| **Access Control Center** | `/access` | admin / dpo | View healthcare permissions + SIH permissions + on-chain roles; grant/revoke SIH roles |
| **Blockchain Explorer** (extend existing `BlockchainExplorer.tsx`) | `/admin/blockchain` | admin / dpo | Existing anchors **plus** contract events (identity/role/NFT/ownership) with explorer links |

## New frontend libs / services

- `lib/wallet.ts` — secp256k1 keygen + signing (via `@noble/secp256k1` or WebCrypto).
  **Private key stays in the browser only**, clearly labeled prototype-grade custody.
- `services/identityService.ts` — DID create/resolve/revoke, challenge/verify.
- `services/assetService.ts` — assets + NFT mint/assign/transfer/verify.

## Navigation

Add an **Identity** and a **Digital Assets** nav group (via `lib/navigation.ts`,
additively). Existing healthcare/privacy/admin nav items are untouched. The user
navigates one unified platform: Healthcare · Privacy · Security · Identity ·
Digital Assets · Blockchain · Administration.

## Constraints

- No new heavy UI framework; reuse existing Tailwind + component system.
- No changes to existing pages' behavior.
- SIH pages render only when `SIH_FEATURES_ENABLED`; otherwise nav items are hidden
  and the app is the pure healthcare platform.

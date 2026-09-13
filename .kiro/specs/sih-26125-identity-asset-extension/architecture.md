# SIH 26125 Identity & Asset Extension — Architecture

> Governing principle: **ADD, DON'T REPLACE.** DPDP Healthcare is PRIMARY.

## Layered additive architecture

```
                         EXISTING USERS (patient/doctor/pharmacy/dpo/admin)
                                        │
                            EXISTING AUTH  (JWT + RBAC + MFA + OAuth)  ← unchanged
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              ▼                                                     ▼
   EXISTING DPDP HEALTHCARE (PRIMARY)                    NEW SIH IDENTITY/ASSET LAYER (additive)
   consent · AES-256 · redaction ·                      DID + ECDSA identity
   chameleon · integrity · RFID · audit                 ContractService (web3.py)
              │                                                     │
              │                                    ┌────────────────┼────────────────┐
              │                                    ▼                ▼                ▼
              │                          IdentityRegistry  PlatformAccessControl  AssetNFT(ERC-721)
              ▼                                                     │
       MongoDB (encrypted PHI, off-chain) ◄──────────── shared ─────┘
              │
   Every action ──► MongoDB hash-chain audit  AND  ──► on-chain contract event  (DUAL AUDIT)
              │
   BlockchainService: [existing hash anchoring]  +  [new contract calls]  → Ganache / Sepolia
```

## Design principles

1. **No destructive changes.** Existing functionality must remain backward-compatible.
   Existing files may be minimally modified where technically necessary for integration,
   provided their existing behavior remains intact and the existing regression suite
   continues to pass. New behavior lives primarily in new services/blueprints/pages/contracts.
2. **Feature-flagged.** SIH layer behind `SIH_FEATURES_ENABLED`; disabling it leaves the
   pure healthcare platform running.
3. **DID is optional per user.** No DID → all existing flows work exactly as today.
4. **On-chain = references only.** Hashes/DIDs/roles/tokenIds/ownership/events. Never PHI.
5. **Dual authorization + dual audit.** Backend and contract both enforce; both audit
   layers coexist.

## Existing files — minimal, backward-compatible modifications where necessary

| File | Modification (behavior-preserving) |
|---|---|
| `backend/app/__init__.py` | Register new blueprints (did, identity, roles, assets, nft, access) |
| `backend/app/db_init.py` | Create 6 new collections + indexes |
| `backend/app/services/blockchain_service.py` | Add contract-call methods; `anchor_record`/`verify_record` remain byte-identical |
| `backend/app/utils/constants.py` | Add `SIHRole` enum; keep `UserRole` |
| `backend/app/middleware/auth_middleware.py` | Add optional `did_verified` helper; `roles_required` unchanged |
| `backend/requirements.txt` | Add `eth-account`, `eth-keys` (web3 already present) |
| `frontend/src/App.tsx`, `lib/navigation.ts` | Add routes + nav items |
| `render.yaml`, `.env.example` | Add contract-address + SIH env vars |

## New components

- **Backend services:** `did_service.py`, `identity_service.py`, `contract_service.py`, `asset_nft_service.py`.
- **Blueprints:** `did/`, `identity/`, `roles/`, `assets/`, `nft/`, `access/`, plus `GET /api/v1/blockchain/events` (added to the existing `blockchain/` blueprint, additively). *(No standalone Flask `contracts` blueprint — chain interaction is handled by the `ContractService`, not an HTTP blueprint.)*
- **Solidity/Hardhat contracts dir (NOT a Flask blueprint):** `contracts/*.sol`, `contracts/test/`, `contracts/scripts/deploy.js`, `contracts/hardhat.config.js`; ABIs exported to `backend/contracts/abi/`.
- **Frontend:** `pages/identity/IdentityCenter.tsx`, `pages/assets/DigitalAssetCenter.tsx`, `pages/access/AccessControlCenter.tsx`; extend `BlockchainExplorer.tsx`; `services/identityService.ts`, `assetService.ts`, `lib/wallet.ts`.

## Graceful degradation (by endpoint class)

If no blockchain is reachable: **read-only** SIH endpoints return HTTP 200 with
`chain_available:false` (serving cached/off-chain data), while **critical write**
operations **fail closed** with HTTP 503 and `chain_available:false`. The healthcare
platform is fully operational and independent of chain availability.

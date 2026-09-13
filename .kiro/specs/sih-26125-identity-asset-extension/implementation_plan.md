# SIH 26125 — 4-Week Implementation Plan

> Each week ends with a **regression gate**: full existing test suite + healthcare
> smoke checks must pass before proceeding.

## Week 1 — DID + Cryptographic Identity + Hardhat Foundation  (zero healthcare risk)
- Scaffold `contracts/` Hardhat project (Ganache + Sepolia networks configured).
- Add `eth-account` / `eth-keys` to `requirements.txt`.
- Create 6 new MongoDB collections + indexes in `db_init.py` (additive).
- Add `SIHRole` enum in `constants.py` (additive).
- Build `did_service` + `did_challenges` + EIP-191 `personal_sign` challenge-response
  wired to the existing JWT pipeline.
- Browser `lib/wallet.ts` (client-side keygen/sign) + Identity Center page + route.
- **Gate:** full regression (164 passed / 1 skipped baseline) + healthcare smoke.

## Week 2 — IdentityRegistry + PlatformAccessControl + ContractService + Blockchain RBAC
- Write + Hardhat-test `IdentityRegistry` (identity only) and `PlatformAccessControl`
  (single role authority). *(AssetNFT is NOT in Week 2.)*
- Deploy the two contracts to Ganache; export ABIs to `backend/contracts/abi/`.
- Build `ContractService` (web3.py): load ABI/address, call, sign.
- Wire DID registration + role grant/revoke on-chain; `roles/` blueprint.
- Dual-enforced RBAC (backend `@roles_required` + on-chain `onlyRole`).
- **Gate:** contract tests green + full regression.

## Week 3 — AssetNFT + NFT APIs + Asset Management + Frontend + Dual Audit
- Write + Hardhat-test `AssetNFT` (ERC-721) — **AssetNFT implementation & testing lives here.**
- Deploy `AssetNFT` to Ganache; export ABI.
- Asset registration (Fernet-encrypted metadata + keccak256 metadata hash); `assets/` blueprint.
- `nft/` blueprint: mint / assign / transfer / verify (dual authorization).
- Digital Asset Center + Access Control Center pages + routes.
- Extend `BlockchainExplorer.tsx` for contract events.
- Dual-audit hook → `chain_events` + existing `AuditService`.
- **Gate:** integration tests + full regression.

## Week 4 — Advanced + Hardening
- Deploy contracts to Sepolia (env addresses, public explorer links).
- Optional RFID gate on high-risk ops (reuse `physical_presence_required`).
- Optional consent ↔ DID bridge (nullable refs).
- Security hardening (reentrancy, nonce, revoke paths) + security test suite.
- Update `docs/demo-script.md` for BOTH workflows (healthcare + SIH identity/asset).
- Extend CI with the Hardhat job.
- **Gate:** all tests green; healthcare demo AND SIH demo both pass.

## Priority order within the month
1. Protect existing DPDP healthcare functionality (continuous).
2. DID + cryptographic identity + Hardhat foundation (Week 1).
3. IdentityRegistry + PlatformAccessControl contracts (Week 2).
4. Blockchain-enforced RBAC (Week 2).
5. AssetNFT (ERC-721) contract + digital assets (Week 3).
6. Admin-controlled minting & assignment (Week 3).
7. Ownership verification & controlled transfer (Week 3).
8. Smart-contract events ↔ existing audit (Week 3).
9. Extend existing hash anchoring (Week 3).
10. RFID for high-risk operations (Week 4, optional).
11. Sepolia deployment (Week 4).
12. Blockchain event indexing/explorer (Week 3–4).
13. DID ↔ consent integration (Week 4, optional).
14. Security hardening + comprehensive regression (Week 4).

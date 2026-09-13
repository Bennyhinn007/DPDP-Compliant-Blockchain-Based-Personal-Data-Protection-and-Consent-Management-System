# SIH 26125 — Implementation Tasks

> Detailed, checkbox task list. **Planning artifact only — do not execute until
> explicit implementation approval.** Each phase ends with the regression gate.

## Phase 1 — Foundation + Identity  (Week 1)
- [ ] 1.1 Scaffold `contracts/` Hardhat project + `hardhat.config.js` (Ganache + Sepolia networks) *(new files)*
- [ ] 1.2 Add `eth-account` / `eth-keys` to `requirements.txt` *(backward-compatible)*
- [ ] 1.3 Add 6 collections + indexes in `db_init.py` *(additive)*
- [ ] 1.4 Add `SIHRole` enum in `constants.py` *(additive)*
- [ ] 1.5 New `did_service.py`: DID gen, DID document, keypair verification *(new)*
- [ ] 1.6 New `did/` blueprint: create / resolve / revoke + challenge / verify *(new)*
- [ ] 1.7 Register `did` blueprint in `__init__.py` *(backward-compatible)*
- [ ] 1.8 `lib/wallet.ts` (browser keygen/sign) + Identity Center page + route *(new + additive route)*
- [ ] 1.9 Tests: DID unit + challenge-response; **run full regression** ✅

## Phase 2 — IdentityRegistry + PlatformAccessControl + RBAC  (Week 2)
- [ ] 2.1 `IdentityRegistry.sol` (identity only — no roles) + Hardhat tests
- [ ] 2.2 `PlatformAccessControl.sol` (OpenZeppelin, single role authority) + tests
- [ ] 2.3 `scripts/deploy.js` → deploy the two contracts to Ganache; export ABIs to `backend/contracts/abi/`
- [ ] 2.4 `contract_service.py` (web3: load ABI/address, call, sign) *(new)*
- [ ] 2.5 Wire DID register + role grant/revoke on-chain; `roles/` blueprint *(new)*
- [ ] 2.6 Dual RBAC (backend `@roles_required` + contract `onlyRole`); **run full regression** ✅

## Phase 3 — AssetNFT + NFT APIs + Frontend + Dual Audit  (Week 3)
- [ ] 3.1 `AssetNFT.sol` (OpenZeppelin ERC-721) + Hardhat tests **(AssetNFT lives in Week 3)**
- [ ] 3.2 Deploy `AssetNFT` to Ganache; export ABI
- [ ] 3.3 `assets/` blueprint + `asset_nft_service.py` (encrypted metadata + keccak256 hash) *(new)*
- [ ] 3.4 `nft/` blueprint: mint / assign / transfer / verify (dual auth) *(new)*
- [ ] 3.5 Digital Asset Center + Access Control Center pages + routes *(new + additive)*
- [ ] 3.6 Extend `BlockchainExplorer.tsx` for contract events *(backward-compatible)*
- [ ] 3.7 Dual-audit hook → `chain_events` + existing `AuditService` *(additive)*
- [ ] 3.8 Integration tests; **run full regression** ✅

## Phase 4 — Advanced + Hardening  (Week 4)
- [ ] 4.1 Deploy contracts to Sepolia; env addresses; explorer links
- [ ] 4.2 Optional RFID gate on mint / DID revoke (reuse `physical_presence_required`)
- [ ] 4.3 Optional consent ↔ DID bridge (nullable refs)
- [ ] 4.4 Security hardening (reentrancy, nonce, revoke paths) + security test suite
- [ ] 4.5 Update `docs/demo-script.md` for both workflows
- [ ] 4.6 Extend CI with Hardhat job; **full regression + both demos green** ✅

## Cross-cutting (all phases)
- [ ] X.1 After every phase: run existing regression suite + healthcare smoke checklist
- [ ] X.2 Keep honesty labels current (real / prototype / simulated)
- [ ] X.3 Keep `SIH_FEATURES_ENABLED` flag functional as the rollback lever
- [ ] X.4 No renaming of existing roles; no PHI on-chain; records never NFTs

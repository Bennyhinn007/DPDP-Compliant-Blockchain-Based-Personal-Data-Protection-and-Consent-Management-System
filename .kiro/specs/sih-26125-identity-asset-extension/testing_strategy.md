# SIH 26125 — Testing Strategy

## Regression gate (highest priority)

**Verified baseline: 164 tests passed, 1 skipped.** All previously-passing tests MUST
continue to pass after every phase (mongomock, no external services) — this is the
merge gate. No phase proceeds on a broken core workflow.

## Test layers

### Backend unit (new)
- `did_service`: keypair verify, DID doc generation, DID format.
- Signature verification (valid/invalid), nonce lifecycle (issue/use/expire/replay).
- `contract_service` (mock web3): call encoding, revert handling, chain-down path.
- `asset_nft_service`: metadata encryption + hash, mint/assign/transfer orchestration.

### Smart-contract (Hardhat / chai)
- Mint authorization (admin only; non-admin reverts)
- Role grant/revoke; ownership after mint/assign
- Controlled transfer (authorized succeeds, unauthorized reverts)
- Revocation blocks operations
- Event emission for every state change
- ReentrancyGuard
- Identity register/revoke/isVerified

### Integration
- End-to-end on Ganache: DID create → challenge/verify login → mint → assign →
  verify ownership → controlled transfer → event appears in `chain_events`.
- Frontend → API → MongoDB → Ganache.

### Security tests
- Unauthorized mint/transfer, role escalation, invalid signature, replay nonce.
- Chain-down graceful degradation (healthcare unaffected).
- Consent still enforced when DID layer active.

### Healthcare smoke (run every phase)
Login · create record · encrypt round-trip · consent grant · doctor consent-gated
access · withdraw → deny · audit hash-chain integrity · integrity verify · redaction/
chameleon workflow · RFID presence.

## CI

Extend `.github/workflows/ci.yml` with a **Hardhat job** (Node) alongside the existing
pytest + frontend build jobs. All three must be green.

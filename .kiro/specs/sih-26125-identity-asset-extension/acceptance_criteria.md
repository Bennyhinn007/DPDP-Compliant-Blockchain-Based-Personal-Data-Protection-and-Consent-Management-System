# SIH 26125 — Acceptance Criteria

## Project-level Definition of Done

1. Every existing healthcare/DPDP workflow works identically — login, records,
   encryption, consent + withdrawal, doctor consent-gated access, audit, integrity
   verification, redaction, chameleon, RFID. ✅ verified by the regression suite.
2. DID creation + ECDSA challenge-response login issues a valid **existing** JWT. ✅
3. Three real Solidity contracts compiled, Hardhat-tested, deployed to Ganache
   (and Sepolia in Week 4). ✅
4. RBAC enforced at BOTH backend and contract levels; unauthorized operations denied
   at both. ✅
5. ERC-721 NFT lifecycle: admin-only mint → assign to DID → ownership verify →
   controlled transfer, with encrypted off-chain metadata + on-chain hash. ✅
6. Healthcare records never become NFTs; no PII/PHI on-chain. ✅ verified.
7. Dual audit: off-chain hash-chain intact + on-chain events cached + viewable. ✅
8. Existing healthcare roles not renamed; SIH roles coexist. ✅
9. No capability falsely claimed; real/prototype/simulated labeled accurately. ✅
10. Both demo workflows (Healthcare DPDP, SIH identity/asset) run on ONE platform. ✅

## Per-requirement acceptance

- Each of R1–R15 (see `requirements.md`) is met per its EARS acceptance criteria.
- 🔴 Critical requirements (R1, R2, R3, R4, R5, R6, R7, R15) are mandatory for MVP.
- 🟠 High (R8, R9, R10, R12) targeted by end of Week 3–4.
- 🟡/🟢 (R11, R13, R14) are Advanced/optional — included only where they materially
  strengthen the platform without risking reliability.

## Verification method

- Automated: pytest regression + new unit/integration tests + Hardhat contract tests, all green in CI.
- Manual demo: run the two end-to-end workflows in `docs/demo-script.md`.
- Honesty audit: every claim in README/PPT/docs cross-checked against actual code status.

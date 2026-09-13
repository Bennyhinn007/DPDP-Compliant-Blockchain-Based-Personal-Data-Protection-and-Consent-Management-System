# SIH 26125 — Security Model

> All existing security controls are **retained**. New controls are additive.
> Honest-labeling rule (R15.3): real vs prototype vs simulated is stated in docs/UI.

## Threat → Mitigation

| Threat | Mitigation |
|---|---|
| DID impersonation | Challenge-response proves private-key possession; verify against registered pubkey; `IdentityRegistry.isVerified` |
| Private-key theft | Keys generated & held client-side, never transmitted; short-lived JWT; DID revocation; hardware-wallet/HSM custody = future work (labeled) |
| Replay attack | Single-use nonce + ≤120s TTL + DID binding + `used` flag |
| Unauthorized NFT mint | `onlyRole(ADMIN)` on-chain AND `@roles_required` backend (dual enforcement) |
| Unauthorized transfer | On-chain role/owner modifiers; transaction reverts |
| Role escalation | Role changes only via ADMIN; emitted as events; audited in both layers |
| Reentrancy | OpenZeppelin `ReentrancyGuard` + checks-effects-interactions |
| Smart-contract vulnerabilities | OpenZeppelin audited libraries; Hardhat test coverage; Ganache→Sepolia staging |
| Access-control bypass (frontend) | Never trust the client; backend AND contract both enforce |
| Unauthorized healthcare-data access | Existing consent + RBAC checks retained unchanged |
| Consent bypass | Existing consent enforcement retained; DID↔consent is additive, not a bypass path |
| On-chain metadata leakage | Only SHA-256 hashes + type on-chain; PHI stays Fernet-encrypted off-chain |
| API authorization bypass | `@jwt_required` + role checks on every new endpoint |
| JWT theft | Existing short expiry, HTTPS, refresh rotation retained |
| Database compromise | Fernet AES-256 retained; on-chain data is only hashes |
| Insider abuse | Dual audit — off-chain hash-chain + immutable on-chain events |
| RFID token replay | Existing 120s one-time presence token; optional gate only |
| Signature forgery | ECDSA secp256k1 verification against the registered public key |

## Cryptography

- **Identity keys:** secp256k1 (ECDSA), reusing `eth-account`/`eth-keys`.
- **DID auth signatures:** EIP-191 `personal_sign`; backend verifies via
  `eth-account.recover_message` (see the DID Signature Scheme in `requirements.md` R3
  and `data_model.md`).
- **On-chain SIH hashes (DID/pubkey/metadata):** **keccak256** → `bytes32`
  (native to Solidity), per the Canonical Derivation section in `data_model.md`.
- **Existing healthcare record anchoring:** **SHA-256** (unchanged, separate subsystem).
- **Data at rest:** existing Fernet AES-256 (unchanged). No PHI on-chain — only hashes.
- **Chameleon hash:** existing real primitive retained; redaction workflow labeled
  accurately (real primitive, simulated anchor workflow).

## Principles

- Dual authorization (application + contract) for all critical operations.
- Least privilege: SIH roles grant only what each operation needs.
- **Chain-availability behavior by endpoint class:** read-only SIH endpoints return
  HTTP 200 with `chain_available:false` (serve cached/off-chain data); critical
  blockchain write operations **fail closed** with HTTP 503 and `chain_available:false`
  (no partial writes). Existing healthcare functionality NEVER depends on chain availability.

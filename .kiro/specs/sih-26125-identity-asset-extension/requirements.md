# SIH 26125 Identity & Asset Extension — Requirements

> **Additive extension** to the existing **DPDP Compliant Redactable Blockchain
> Healthcare & Pharmacy Platform**. Healthcare/DPDP remains the PRIMARY system.
> Governing principle: **ADD, DON'T REPLACE.**

---

## 0. Context & Non-Negotiables

**Existing project (PRIMARY, must remain fully functional):** DPDP healthcare
platform — patient/doctor/pharmacy/DPO/admin workflows, healthcare records,
consent management + withdrawal, AES-256/Fernet encryption, JWT auth, RBAC, MFA
(TOTP), WebAuthn, hash-chained audit, blockchain hash anchoring, integrity
verification, **real chameleon-hash primitive** (`chameleon_crypto.py`) +
simulated redaction workflow (`chameleon_hash_service.py`), RFID physical
presence, React frontend, **verified test baseline: 164 passed, 1 skipped**, CI.

**This extension adds (from SIH PS 26125):** Decentralized Identity (DID) +
cryptographic identity, real Solidity smart contracts (Hardhat + OpenZeppelin),
blockchain-enforced RBAC, ERC-721 NFT digital-asset management, admin-controlled
minting/assignment, ownership verification + controlled transfer, on-chain event
audit (second audit layer), Sepolia deployment, blockchain event explorer,
optional consent↔DID and RFID-gated high-risk operations.

**Hard rules:**
- Do NOT migrate, replace, rebrand, or delete existing healthcare functionality.
- Healthcare records stay **encrypted, off-chain** — NEVER turned into NFTs, never on-chain.
- Do NOT rename existing roles (patient/doctor/pharmacy_staff/dpo/admin). SIH roles
  (Manager/Auditor/User) are added **alongside** via a flexible mapping.
- Only hashes/DIDs/roles/tokenIds/ownership/permission-state/events go on-chain.
- No AI, no extra blockchains, no extra databases, no microservices, no new hardware
  beyond existing RFID.
- **No destructive changes. Existing functionality must remain backward-compatible.
  Existing files may be minimally modified where technically necessary for
  integration, provided their existing behavior remains intact and the existing
  regression suite continues to pass.**
- After every phase: full existing regression suite must pass.

---

## Requirement Notation

Each requirement uses EARS-style acceptance criteria. Priority: 🔴 Critical /
🟠 High / 🟡 Medium / 🟢 Optional.

---

## R1 — Preserve Existing Platform (🔴 Critical, cross-cutting)

**User story:** As the platform owner, I want all existing DPDP healthcare
functionality to keep working unchanged, so that the extension strengthens rather
than risks the primary product.

**Acceptance criteria:**
1. WHEN the SIH extension is deployed THEN all existing `/api/v1/*` healthcare
   endpoints SHALL respond identically to before.
2. WHEN the existing test suite runs THEN 100% of previously-passing tests SHALL pass.
3. WHEN a user without a DID uses the platform THEN every existing workflow
   (login, records, consent, doctor access, audit, redaction, RFID) SHALL work.
4. The system SHALL NOT delete, rename, or alter the semantics of any existing
   MongoDB collection, role, or API.
5. Where an existing file must be modified for integration, the modification SHALL
   be backward-compatible and SHALL preserve existing behavior.

---

## R2 — Decentralized Identity (DID) Layer (🔴 Critical)

**User story:** As a user, I want an optional decentralized identity linked to my
existing account, so that my identity is cryptographically verifiable and
independent of a central password.

**Acceptance criteria:**
1. WHEN an authenticated user requests DID creation THEN the system SHALL generate
   a secp256k1 keypair (private key **client-side only**) and register a DID of the
   form `did:rakshaid:<identifier>`.
2. The system SHALL store a DID Document off-chain (MongoDB `dids`) containing the
   public key, status, created timestamp, controller, and linked existing `user_id`.
3. The system SHALL preserve the existing `user_id` — the DID is an **additional**
   identity layer, never a replacement.
4. WHEN a DID is created THEN a hash of the DID + public key SHALL be registered
   on-chain via `IdentityRegistry`.
5. WHEN an admin revokes a DID THEN `IdentityRegistry` status SHALL become revoked
   AND subsequent DID verification SHALL fail.
6. The system SHALL clearly label the DID method as **prototype** (not an
   interoperable production DID network) in docs and UI.

---

## R3 — Cryptographic Identity Proof (🔴 Critical)

**User story:** As a user, I want to authenticate by proving possession of my
private key, so that identity verification does not rely solely on a password.

**Signature scheme (standardized — EIP-191 `personal_sign`):**
- **Nonce:** backend generates 32 cryptographically-random bytes, `0x`-prefixed hex,
  stored in `did_challenges { did, nonce, expires_at, used }` with a ≤120s expiry and
  a `used` flag.
- **Message to sign (exact format):**
  `DPDP-DID-AUTH|did=<full_did_string>|nonce=<0x-hex-nonce>|exp=<unix_seconds>`
  as a UTF-8 string. The DID and nonce are bound INTO the signed message (prevents
  cross-DID / cross-session replay).
- **Signing:** frontend signs the UTF-8 message via EIP-191 `personal_sign`
  (the Ethereum `\x19Ethereum Signed Message:\n<len>` prefix) using the client-side
  secp256k1 private key.
- **Verification:** backend recovers the signer with
  `eth_account.Account.recover_message(encode_defunct(text=message), signature=sig)`
  and confirms the recovered address/pubkey matches the DID's registered public key
  (see `pubKeyHash` derivation in `data_model.md`). Frontend and backend use this
  identical EIP-191 format.

**Acceptance criteria:**
1. WHEN a user requests DID authentication THEN the backend SHALL issue a single-use
   nonce (32 bytes, ≤120s TTL, bound to the DID) stored in `did_challenges`.
2. WHEN the user submits an EIP-191 `personal_sign` signature over the exact message
   format above THEN the backend SHALL verify it via `eth-account.recover_message`
   (or an exactly compatible equivalent) against the registered public key.
3. IF the signature is valid AND the DID is active (`IdentityRegistry.isVerified`)
   AND the DID is linked to an existing `user_id` THEN the system SHALL issue the
   **existing JWT** access/refresh token pair (reusing `AuthService`), with `sub`
   set to that `user_id`.
4. WHEN a nonce is used once OR expires (or the `exp` in the message has passed) THEN
   it SHALL NOT be accepted again. Replay protection is enforced by **application-level
   checks** — verification rejects `used == true` and `now > expires_at`; it does NOT
   rely on a MongoDB TTL index. Expired/used challenges may be cleaned up opportunistically
   or periodically (hygiene only; correctness never depends on cleanup).
5. The existing password, Google OAuth, and MFA login flows SHALL continue to work unchanged.
6. DID authentication SHALL be an **additional** mechanism, not a replacement for JWT.
7. DID login SHALL be permitted ONLY when the DID is already linked to a `user_id`
   (the link is created in the Identity Center at DID creation).

---

## R4 — Real Solidity Smart Contracts (🔴 Critical)

**User story:** As a judge/auditor, I want genuine on-chain smart contracts, so
that identity, access, and asset rules are enforced by the blockchain, not just the backend.

**Acceptance criteria:**
1. The system SHALL include real Solidity contracts compiled and tested with Hardhat,
   using OpenZeppelin libraries.
2. `IdentityRegistry.sol` SHALL support register / revoke / isVerified (identity only —
   it SHALL NOT store or manage roles).
3. `PlatformAccessControl.sol` SHALL be the SINGLE authority enforcing roles
   ADMIN/MANAGER/AUDITOR/USER using OpenZeppelin AccessControl.
4. `AssetNFT.sol` SHALL be ERC-721 with admin-gated minting, controlled transfer,
   metadata-hash storage, and status.
5. Contracts SHALL deploy to Ganache (dev) and Sepolia (public testnet).
6. WHEN a contract call violates a role/ownership rule THEN the transaction SHALL revert.
7. The existing `BlockchainService` hash-anchoring SHALL continue to function unchanged.

---

## R5 — Blockchain-Enforced RBAC (🔴 Critical)

**User story:** As an admin, I want critical operations enforced by both the
backend and the smart contract, so that authorization cannot be bypassed via the frontend.

**Acceptance criteria:**
1. The system SHALL define SIH roles (ADMIN/MANAGER/AUDITOR/USER) **in addition to**
   existing healthcare roles, via a flexible mapping (config-driven).
2. Critical operations (mint, assign, transfer, role change, revoke) SHALL be gated
   by BOTH `@roles_required` (backend) AND an on-chain `onlyRole` modifier.
3. Existing healthcare RBAC (`@roles_required("patient"|"doctor"|...)`) SHALL be unchanged.
4. WHEN an unauthorized actor attempts a gated operation THEN both layers SHALL deny it.

---

## R6 — ERC-721 Digital Assets (🔴 Critical)

**User story:** As an organization, I want to represent digital/organizational
assets as NFTs linked to identities, so that ownership is unique, traceable, and verifiable.

**Acceptance criteria:**
1. The system SHALL register digital assets (e.g., medical equipment certificate,
   software license, equipment ownership record) with **synthetic demo data**.
2. Sensitive asset metadata SHALL be stored **encrypted off-chain** (MongoDB `assets`);
   only a SHA-256 metadata hash + asset type + status + owner DID SHALL be on-chain.
3. Healthcare records SHALL NOT be represented as NFTs and SHALL remain in their
   existing encrypted collections.
4. WHEN an asset is minted THEN a `tokenId` SHALL be linked to an owner DID.

---

## R7 — Admin-Controlled Minting & Assignment (🔴 Critical)

**Acceptance criteria:**
1. WHEN a non-admin attempts to mint an NFT THEN the operation SHALL be denied at
   both backend and contract level.
2. WHEN an admin mints an NFT THEN it SHALL be assignable to a target DID.
3. WHEN an asset is minted/assigned THEN a MongoDB `nft_tokens` record AND an
   on-chain event SHALL be created.
4. *(Optional Advanced)* WHEN RFID gating is enabled THEN minting SHALL additionally
   require a valid physical-presence token.

---

## R8 — Ownership Verification & Controlled Transfer (🟠 High)

**Acceptance criteria:**
1. WHEN any user verifies an asset THEN the system SHALL return on-chain `ownerOf`
   AND confirm `SHA256(decrypt(metadata)) == on-chain metadataHash`.
2. WHEN a transfer is attempted THEN the contract SHALL enforce role/ownership rules
   and revert if unauthorized.
3. WHEN a transfer succeeds THEN ownership SHALL update on-chain and in `nft_tokens`,
   and an event SHALL be recorded.

---

## R9 — Dual Audit (on-chain events + existing hash-chain) (🟠 High)

**User story:** As an auditor, I want both the detailed off-chain audit and an
immutable on-chain event history, so that I can verify actions at two independent levels.

**Acceptance criteria:**
1. The existing MongoDB hash-chained `audit_logs` SHALL remain unchanged and continue
   recording all existing events.
2. WHEN a smart-contract operation occurs THEN its event SHALL be recorded on-chain
   AND cached in MongoDB `chain_events`.
3. The system SHALL NOT replace the off-chain audit with the on-chain audit.
4. WHEN an auditor views history THEN both layers SHALL be presentable together.

---

## R10 — Extend Existing Blockchain Hash Anchoring (🟠 High)

**Acceptance criteria:**
1. `BlockchainService` SHALL retain `anchor_record` / `verify_record` behavior exactly.
2. The system SHALL add contract-interaction methods **alongside** existing anchoring
   (new methods; no signature changes to existing ones).

---

## R11 — RFID for High-Risk Operations (🟢 Optional / Advanced)

**Acceptance criteria:**
1. The existing RFID/physical-presence functionality SHALL remain unchanged and
   SHALL NOT become a dependency for normal healthcare workflows.
2. WHEN RFID gating is explicitly enabled for an operation (e.g., NFT mint, DID revoke)
   THEN a valid physical-presence token SHALL be required in addition to normal auth.

---

## R12 — Sepolia Deployment (🟠 High / Advanced)

**Acceptance criteria:**
1. Contracts SHALL be deployable to Sepolia with addresses configured via env vars.
2. WHEN on Sepolia THEN the explorer SHALL show public block-explorer links for txns.
3. The system SHALL default to Ganache and degrade gracefully if no chain is reachable.

---

## R13 — Blockchain Event Explorer (🟡 Medium / Advanced)

**Acceptance criteria:**
1. The existing `BlockchainExplorer.tsx` SHALL be **extended** (not replaced) to show
   contract events: identity, role, NFT mint/assign/transfer, ownership, permission.
2. WHEN a user opens the explorer THEN it SHALL list cached `chain_events` with links.

---

## R14 — DID ↔ Consent Integration (🟢 Optional)

**Acceptance criteria:**
1. WHERE technically appropriate, consent grants MAY reference patient/doctor DIDs.
2. The existing consent workflow SHALL continue to work for users **without** DIDs.
3. This integration SHALL be additive and reversible.

---

## R15 — Security & Regression (🔴 Critical, cross-cutting)

**Acceptance criteria:**
1. The system SHALL retain all existing security controls (JWT expiry, lockout,
   Fernet encryption, hash-chain audit, RFID).
2. New controls SHALL address: DID impersonation, private-key theft, replay,
   unauthorized mint/transfer, role escalation, reentrancy, contract vulnerabilities,
   consent bypass, on-chain metadata leakage.
3. The system SHALL NOT falsely claim any capability as implemented; simulated /
   prototype / planned features SHALL be labeled accurately.
4. After each phase, the full existing regression suite SHALL pass before proceeding.

---

## Out of Scope (explicitly)

- Turning healthcare records into NFTs.
- Storing any PII/PHI on-chain.
- Replacing JWT/password/OAuth/MFA auth.
- Renaming existing healthcare roles.
- Production-grade DID network interoperability (prototype only).
- Hardware-wallet / HSM key custody (noted as future work).
- AI/ML, additional chains, additional databases, microservices.

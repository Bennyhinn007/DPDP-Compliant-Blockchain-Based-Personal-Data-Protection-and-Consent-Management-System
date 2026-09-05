# Threat Model & Security Analysis

DPDP-Compliant Redactable-Blockchain Healthcare Platform

This document states, honestly, what the system defends against, how, and
where its limits are. A security system is only credible if it is explicit
about both its guarantees and its assumptions.

---

## 1. Assets we protect

| Asset | Why it matters |
|-------|----------------|
| Patient personal & health data (PII/PHI) | Sensitive under the DPDP Act; core of the platform |
| Consent records | Legal basis for every processing action |
| Audit trail | Tamper-evidence and accountability |
| Record integrity (anchors) | Proves data has not been silently altered |
| Redaction trapdoor key | Grants the power to perform authorized redactions |
| Authentication credentials & sessions | Gate to everything above |

## 2. Trust boundaries

1. **Browser ↔ API** — all traffic crosses the network; treated as untrusted, authenticated per request via JWT.
2. **API ↔ MongoDB** — the datastore is trusted for availability but NOT for confidentiality (sensitive fields are encrypted before they reach it).
3. **API ↔ Blockchain** — the chain is an external, append-only integrity oracle. No PII ever crosses this boundary — only SHA-256 hashes.
4. **API ↔ RFID terminal (ESP32)** — a physical device on the local network that asserts "a specific card was physically tapped."

## 3. Adversaries considered

- **A1 — Credential thief:** has a stolen password.
- **A2 — Malicious/compromised insider:** has some legitimate DB or app access.
- **A3 — Network attacker:** can observe or tamper with traffic.
- **A4 — Curious datastore reader:** can read MongoDB at rest (e.g. stolen backup).
- **A5 — Unauthorized redactor:** wants to alter/delete records while keeping the anchor "valid."

---

## 4. Threats → Mitigations

### T1. Stolen password used to act on sensitive data — *A1*
**Mitigation.** Password (something you know) is not sufficient for sensitive, irreversible operations. Data erasure and all state-changing DPO actions require a **physical RFID tap** — a short-lived (2-minute) physical-presence token proving the actor is bodily present. This is hardware step-up authentication: *something you know + something you physically have*.
**Residual risk.** An attacker who also physically steals the card within the window. Mitigated by short token lifetime and audit logging of every tap.

### T2. Silent tampering with a record — *A2, A4*
**Mitigation.** Every record's SHA-256 hash is anchored on a blockchain. Verification recomputes the hash and compares it to the anchor. Any unauthorized change produces a mismatch → `INTEGRITY_VIOLATION`. This is demonstrated live by the tamper-attempt demo.
**Residual risk.** An attacker who can also forge/replace the anchor. On a public chain (Sepolia) this is infeasible; on a single local node it depends on node integrity (see limitations).

### T3. Unauthorized redaction that still "verifies" — *A5*
**Mitigation.** Lawful redaction (correction/erasure) uses a **chameleon hash** collision: `CH(m, r) = g^m · y^r mod p`. Finding `r'` such that `CH(m, r) = CH(m', r')` requires the secret **trapdoor `x`**. Without it, producing a colliding redaction is as hard as the discrete-log problem in a 1536-bit group. So an attacker cannot fabricate an "authorized-looking" edit.
**Residual risk.** Compromise of the trapdoor key itself (see limitations — key management).

### T4. Data exposure from a stolen datastore/backup — *A4*
**Mitigation.** Sensitive fields (name, phone, address, clinical notes, etc.) are encrypted with AES (Fernet) **before** insertion. MongoDB stores ciphertext; plaintext only exists transiently in the API after decryption. Email is stored as a SHA-256 hash for indexed lookup plus an encrypted copy.
**Residual risk.** Compromise of the encryption key. Keys are environment-provided, never committed.

### T5. Network interception / tampering — *A3*
**Mitigation.** JWTs are signed (HS256 dev / RS256 prod) with issuer + audience claims and short access-token lifetimes; refresh tokens are separate. CORS is restricted to known origins. In production the platform is served over TLS.
**Residual risk.** TLS termination/config is a deployment responsibility.

### T6. Brute-force / credential stuffing — *A1*
**Mitigation.** bcrypt password hashing (cost 12) and **role-based account lockout** after repeated failures (patients 30 min, admins up to 2 h). Lockouts are audited as `critical`.

### T7. Repudiation ("I never did that") — *A2*
**Mitigation.** A hash-chained, append-only audit log records actor, action, resource, reason, and severity for every sensitive event, including redactions (with the chameleon proof) and physical taps.
**Residual risk.** The audit store shares the DB trust boundary; anchoring audit-log hashes strengthens this.

### T8. Privilege escalation across roles — *A2*
**Mitigation.** Every route is guarded by `@jwt_required` + `@roles_required(...)`; ownership checks ensure patients can only touch their own records. Google OAuth sign-ups default to the least-privileged `patient` role.

---

## 5. What we deliberately do NOT store on-chain
Only SHA-256 **hashes** are anchored. No name, diagnosis, or any PII ever touches the blockchain. This keeps the chain useful as an integrity oracle while remaining DPDP-compliant (on-chain data would be effectively un-erasable).

## 6. Honest limitations (future work)

- **Trapdoor key management.** The chameleon trapdoor is the crown jewel. Production should hold it in an HSM / KMS with threshold control and rotation, not a process environment variable.
- **Single-node chain.** Local Ganache is a single point of trust. The Sepolia option addresses this by anchoring to a public, decentralized testnet with an independently verifiable explorer link; a production mainnet/consortium chain would be stronger still.
- **Blockchain anchor still uses SHA-256.** The chameleon hash secures *authorized redaction semantics*; the on-chain anchor is a standard SHA-256 commitment. Both are real; they serve different purposes.
- **Encryption key rotation** is defined (90-day policy) but automated rotation tooling is not yet implemented.
- **RFID trust.** The terminal asserts physical presence over the local network; a hardened deployment would mutually authenticate the terminal to the API.

## 7. Compliance mapping (DPDP Act)

| DPDP principle | Mechanism |
|----------------|-----------|
| Right to correction & erasure (S.12) | Chameleon-hash redaction with preserved anchor + audit |
| Consent-driven processing | Consent lifecycle + receipts, enforced per request |
| Data minimisation / residency | Field-level encryption; hashes-only on-chain; India residency config |
| Accountability | Hash-chained audit trail; physical-presence gating |

---

*This threat model is intentionally explicit about residual risk. Where a
control has limits, they are stated rather than hidden — which is itself part
of the security posture.*

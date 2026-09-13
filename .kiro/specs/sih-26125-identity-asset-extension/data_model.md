# SIH 26125 — Data Model Changes

> Existing 11 MongoDB collections remain **UNCHANGED**. 6 new collections added.
> Additive fields on existing collections are nullable/defaulted and
> backward-compatible (existing documents remain valid).

## New collections

| Collection | Key fields | Purpose |
|---|---|---|
| `dids` | `_id`(did string), `user_id`(FK→users), `public_key`, `pub_key_hash`, `status`(active/revoked), `sih_role`, `did_document`(JSON), `created_at`, `updated_at` | DID ↔ existing user link |
| `did_challenges` | `_id`, `did`, `nonce`(32B hex), `expires_at`(≤120s, existing ISO-string timestamp convention), `used`(bool), `created_at` | Replay-protected challenge-response (application-level expiry — see note) |
| `assets` | `_id`, `asset_type`, `name`*, `description`*, `spec`*, `document`* (Fernet-encrypted), `metadata_hash`(keccak256, see Canonical Derivation), `created_by`, `created_at` | Off-chain encrypted asset metadata |
| `nft_tokens` | `_id`, `token_id`(on-chain), `owner_did`, `asset_id`(FK→assets), `metadata_hash`, `mint_tx`, `status`, `created_at`, `updated_at` | NFT ↔ DID ↔ asset mapping |
| `role_assignments` | `_id`, `did`, `sih_role`, `granted_by`, `grant_tx`, `status`, `created_at` | On-chain SIH-role mirror cache |
| `chain_events` | `_id`, `event_name`, `contract`, `tx_hash`, `block_number`, `args`(JSON), `indexed_at` | On-chain event cache (explorer + dual audit) |

`*` = encrypted via existing `EncryptionService`.

## Encryption

`assets` sensitive fields (`name`, `description`, `spec`, `document`) join the
existing `SENSITIVE_FIELDS` set (backward-compatible addition) → reuses Fernet
AES-256. No PHI ever leaves MongoDB; only **keccak256** metadata hashes go on-chain
(see Canonical Derivation & Encoding below). SHA-256 remains reserved for the existing
healthcare record anchoring subsystem.

## `did_challenges` expiry — APPLICATION-LEVEL (no MongoDB TTL)

Challenge validity is enforced **entirely in application code**, not by a MongoDB TTL index:

- `expires_at` follows the existing project's timestamp convention (ISO-8601 UTC string
  via `utc_now()`), consistent with the rest of the codebase. **No BSON `Date` migration
  is introduced solely for DID challenges.**
- Verification (`POST /api/v1/did/verify`) MUST reject a challenge if `now > expires_at`
  (expired) OR if `used == true` (already consumed). On success it sets `used = true`.
- Challenge validity MUST NOT depend on a MongoDB TTL index (TTL indexes require BSON
  `Date` and would silently fail on ISO strings — explicitly avoided).
- Expired/used challenges MAY be cleaned up **opportunistically** (e.g., on the next
  verify/challenge call for that DID) or **periodically** (a lightweight sweep). Cleanup
  is a hygiene optimization only; correctness never relies on it, because verification
  independently rejects expired/used challenges.

## Indexes

- `dids`: `user_id` unique, `status`
- `did_challenges`: `nonce` unique  *(index for lookup only; NOT a TTL index — expiry is application-level)*
- `assets`: `asset_type`, `created_at`
- `nft_tokens`: `token_id` unique, `owner_did`
- `role_assignments`: `did`, `sih_role`
- `chain_events`: `tx_hash` unique, `event_name`+`block_number`

## Additive fields on existing collections (nullable, default null)

| Collection | New optional field | Notes |
|---|---|---|
| `users` | `did` (nullable ref) | Links a user to their DID; absence = pure existing behavior |
| `consents` | `patient_did`, `doctor_did` (nullable) | R14 optional DID↔consent bridge |

All additive fields default to null so pre-existing documents remain valid and all
existing queries continue to function. Dropping these fields is non-destructive.

## Canonical Derivation & Encoding (identical across frontend, backend, MongoDB, Solidity)

These rules are the single source of truth. All four layers MUST follow them exactly
so hashes/identifiers match at every boundary.

**Keypair.** secp256k1. Public key represented in **uncompressed** form: 65 bytes,
`0x04 || X(32) || Y(32)`. Stored in `dids.public_key` as a `0x`-prefixed lowercase hex string.

**`pubKeyHash` (on-chain `bytes32`).** `keccak256(uncompressed_public_key_bytes)` where
the input is the raw 65 bytes (including the `0x04` prefix). Result is a 32-byte value;
stored in `dids.pub_key_hash` as `0x`-prefixed lowercase hex, passed to Solidity as `bytes32`.

**DID identifier.** `did:rakshaid:<identifier>` where
`<identifier> = base58btc( keccak256(uncompressed_public_key_bytes)[0:16] )`
(first 16 bytes of the keccak256 pubkey hash, Base58-encoded). This yields a stable,
collision-resistant, human-friendly identifier. The full DID string is stored as `dids._id`.

**`didHash` (on-chain `bytes32`).** `keccak256(utf8bytes(full_did_string))`. Solidity,
backend, and frontend all compute `keccak256` over the exact UTF-8 bytes of the DID
string `did:rakshaid:<identifier>`. Stored where needed as `0x`-prefixed lowercase hex.

**`metadataHash` (on-chain `bytes32`).** `keccak256(canonical_metadata_bytes)` where
`canonical_metadata_bytes = utf8( JSON.stringify(plaintext_metadata, sorted keys, no whitespace) )`.
NOTE: on-chain uses **keccak256** (native to Solidity/`bytes32`). The plaintext metadata
is hashed BEFORE encryption; the ciphertext is stored in `assets`, the keccak256 hash
on-chain, and `assets.metadata_hash` stores the same `0x`-prefixed hex for verification.
(Existing SHA-256 record-anchoring in `BlockchainService` is unchanged and separate.)

**Hex ↔ bytes32 rules.** All on-chain 32-byte values are exchanged as `0x`-prefixed,
lowercase, 64-hex-char strings. Backend converts with `Web3.to_bytes(hexstr=...)` /
`Web3.to_hex(...)`; frontend uses the same `0x`-prefixed lowercase convention; MongoDB
stores the `0x`-prefixed hex string form. No implicit case changes or prefix stripping.

**Rationale for keccak256 (not SHA-256) for DID/metadata hashes:** keccak256 is the
native Solidity hash and maps cleanly to `bytes32`, avoiding cross-hash mismatches on-chain.
SHA-256 remains reserved for the existing healthcare record anchoring in `BlockchainService`
(unchanged), keeping the two subsystems independent.

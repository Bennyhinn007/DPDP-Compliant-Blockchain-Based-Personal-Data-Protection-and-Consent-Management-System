# SIH 26125 — API Changes

> All existing `/api/v1/*` endpoints remain **UNCHANGED**. New endpoints below.
> Each new endpoint uses `@jwt_required` plus role/on-chain checks as noted.

| Method | Endpoint | Auth | Purpose | Chain call | DB |
|---|---|---|---|---|---|
| POST | `/api/v1/did` | jwt | Create DID (client submits pubkey) | IdentityRegistry.register | `dids` |
| GET | `/api/v1/did/:did` | jwt | Resolve DID document | isVerified | `dids` |
| POST | `/api/v1/did/:did/revoke` | jwt+admin (+RFID opt) | Revoke DID | revoke | `dids` |
| POST | `/api/v1/did/challenge` | none | Issue single-use nonce | — | `did_challenges` |
| POST | `/api/v1/did/verify` | none | Verify signature → **existing JWT** | isVerified | `did_challenges` |
| GET | `/api/v1/identity/me` | jwt | My DID + status + role | isVerified + PlatformAccessControl.hasRole | `dids` |
| POST | `/api/v1/roles/grant` | jwt+admin | Grant SIH role | grantRole | `role_assignments` |
| POST | `/api/v1/roles/revoke` | jwt+admin | Revoke SIH role | revokeRole | `role_assignments` |
| GET | `/api/v1/roles/matrix` | jwt | Permission matrix | hasRole | — |
| POST | `/api/v1/assets` | jwt+admin/manager | Register asset (encrypted metadata) | — | `assets` |
| GET | `/api/v1/assets` | jwt | List assets | — | `assets` |
| GET | `/api/v1/assets/:id` | jwt | Asset detail (decrypted per authz) | — | `assets` |
| POST | `/api/v1/nft/mint` | jwt+admin (+RFID opt) | Mint NFT to a DID | mint | `nft_tokens` |
| POST | `/api/v1/nft/:id/assign` | jwt+admin/manager | Assign NFT to DID | assign | `nft_tokens` |
| POST | `/api/v1/nft/:id/transfer` | jwt (role/owner) | Controlled transfer | controlledTransfer | `nft_tokens` |
| GET | `/api/v1/nft/:id/verify` | jwt | Ownership + metadata-hash verify | ownerDidOf | `nft_tokens`,`assets` |
| GET | `/api/v1/nft` | jwt | List NFTs (by owner DID) | — | `nft_tokens` |
| GET | `/api/v1/blockchain/events` | jwt | List cached contract events | — | `chain_events` |
| GET | `/api/v1/access/check` | jwt | Dual-authorization check | hasRole | — |

## Conventions

- Reuse the existing error middleware and JSON envelope shape.
- Contract reverts → HTTP 403/422 with a clear message.
- **Chain-availability behavior by endpoint class:**
  - **Read-only SIH endpoints** (GET `/did/:did`, `/identity/me`, `/roles/matrix`,
    `/assets`, `/assets/:id`, `/nft`, `/nft/:id/verify`, `/blockchain/events`,
    `/access/check`): when the chain is unreachable, return **HTTP 200** with
    `{ "chain_available": false }` and serve cached/off-chain data where appropriate
    (e.g., `chain_events`, `nft_tokens`, `assets`).
  - **Critical blockchain write operations** (POST `/did`, `/did/:did/revoke`,
    `/roles/grant`, `/roles/revoke`, `/nft/mint`, `/nft/:id/assign`,
    `/nft/:id/transfer`): **fail closed** with **HTTP 503** and
    `{ "chain_available": false }` — no partial state is written.
  - **Existing healthcare endpoints NEVER depend on chain availability** and are unaffected.
- DID auth endpoints (`/api/v1/did/challenge`, `/api/v1/did/verify`) live in the
  **new `did/` blueprint** and are public (no JWT) because they PRODUCE a JWT,
  mirroring the existing `/auth/login` pattern. The existing `auth/` blueprint
  (`auth/routes.py`) is **NOT modified** for DID authentication.
- New blueprints are registered additively in `app/__init__.py`; existing blueprint
  registrations are untouched.

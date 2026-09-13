# SIH 26125 — Smart Contract Design

## Toolchain

Hardhat (JS) + OpenZeppelin Contracts v5 + Solidity ^0.8.24. Compile/test locally →
deploy to Ganache (chainId 1337) → Sepolia (11155111). ABIs + deployed addresses
exported to `backend/contracts/abi/` and env vars. **3 contracts** (deliberately
minimal — asset/audit registries folded into events to avoid overengineering).

**Prerequisite:** Node.js + Hardhat toolchain installed alongside the Python stack.

## Role source of truth (single authority)

`PlatformAccessControl` is the **SINGLE authoritative on-chain SIH role authority**.
`IdentityRegistry` is identity-only (registration, verification status, public-key
binding, revocation) and does **NOT** store or manage roles. This removes the
dual-store drift risk: any component needing a role check reads `PlatformAccessControl.hasRole`.

## IdentityRegistry.sol  (identity only — no roles)

```
State: mapping(bytes32 didHash => Identity)
       Identity { bytes32 pubKeyHash; uint8 status; uint256 registeredAt; }
       // status: 0 = none, 1 = active, 2 = revoked
Functions:
  register(bytes32 didHash, bytes32 pubKeyHash)   // onlyRole(ADMIN) [role checked via PlatformAccessControl]
  revoke(bytes32 didHash)                          // onlyRole(ADMIN)
  isVerified(bytes32 didHash) view returns (bool)  // true iff status == active
  pubKeyHashOf(bytes32 didHash) view returns (bytes32)
Events: IdentityRegistered(didHash, pubKeyHash), IdentityRevoked(didHash)
Security: reads role from PlatformAccessControl; no external calls beyond that; checks-effects-interactions.
NOTE: role/setRole/roleOf were REMOVED — roles are owned solely by PlatformAccessControl.
```

## PlatformAccessControl.sol  (single role authority)

```
Extends: OpenZeppelin AccessControlEnumerable
Roles (bytes32 = keccak256("ROLE")): ADMIN_ROLE, MANAGER_ROLE, AUDITOR_ROLE, USER_ROLE
Functions: grantRole / revokeRole (OZ), hasRole (OZ), helper hasAnyRole()
Modifiers: onlyRole(...) consumed by IdentityRegistry (register/revoke) AND AssetNFT
           (mint/assign/transfer) — this contract is the ONLY role authority.
Events: RoleGranted / RoleRevoked (OZ built-in)  → part of the on-chain audit
DEFAULT_ADMIN_ROLE assigned to the deployer (backend admin key).
Note: SIH roles are keyed here by the actor's didHash (or address); `roleOf(didHash)`
      semantics, if needed for display, are served by hasRole checks — no second store.
```

## AssetNFT.sol

```
Extends: ERC721, ERC721URIStorage, ReentrancyGuard; references PlatformAccessControl
State: mapping(uint256 tokenId => Asset)
       Asset { bytes32 ownerDidHash; bytes32 metadataHash; uint8 assetType; uint8 status; }
Functions:
  mint(bytes32 toDidHash, bytes32 metadataHash, uint8 assetType)
      onlyRole(ADMIN) nonReentrant returns (uint256 tokenId)
  assign(uint256 tokenId, bytes32 toDidHash)          // onlyRole(ADMIN | MANAGER)
  controlledTransfer(uint256 tokenId, bytes32 toDidHash)  // role/owner checks; revert otherwise
  ownerDidOf(uint256) view; metadataHashOf(uint256) view; statusOf(uint256) view
  setStatus(uint256, uint8) onlyRole(ADMIN)           // e.g., REVOKED
Events: AssetMinted, AssetAssigned, AssetTransferred, AssetStatusChanged  → on-chain audit trail
Security: onlyRole gating, ReentrancyGuard, no PHI, hashes only.
```

## Off-chain / on-chain relationship

Hash/identifier derivation follows the **Canonical Derivation & Encoding** section in
`data_model.md` (single source of truth). On-chain SIH hashes use **keccak256** (native
`bytes32`); the existing healthcare record anchoring keeps using SHA-256, separately.

```
NFT tokenId ─ ownerDidHash ─ metadataHash(keccak256) ─ assetType ─ status     [ON-CHAIN, bytes32]
                                     │
                                     └── MongoDB `assets` (Fernet-encrypted: name, spec, docs)  [OFF-CHAIN]
Verify: ownerDidOf(tokenId)  AND  keccak256(canonical(decrypt(asset))) == metadataHashOf(tokenId)
```

## Contract tests (Hardhat / chai)

- Mint authorization (admin only; non-admin reverts)
- Role grant / revoke correctness
- Ownership correctness after mint / assign
- Controlled transfer rules (authorized succeeds, unauthorized reverts)
- Revocation (status → REVOKED blocks operations)
- Event emission for every state change
- ReentrancyGuard behavior
- Identity register / revoke / isVerified

## Deployment

`scripts/deploy.js` deploys the 3 contracts, wires roles, writes addresses +
ABIs to `backend/contracts/abi/`. Ganache first; Sepolia in Week 4 via env-configured
RPC + funded key.

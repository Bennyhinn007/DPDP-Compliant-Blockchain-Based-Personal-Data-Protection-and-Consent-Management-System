# SIH 26125 Smart Contracts (additive)

Solidity/Hardhat project for the SIH 26125 identity/access/asset extension. This is
**additive** to the existing DPDP healthcare platform and does not modify any existing
backend, frontend, database, or healthcare functionality.

> **Status:** Week 1 scaffold only. The three contracts
> (`IdentityRegistry.sol`, `PlatformAccessControl.sol`, `AssetNFT.sol`) are authored,
> tested, and deployed in **Week 2 (Identity + AccessControl)** and **Week 3 (AssetNFT)**
> per `.kiro/specs/sih-26125-identity-asset-extension/implementation_plan.md`.
> No Solidity contract code exists yet.

## Layout

```
contracts/
├── package.json         # Hardhat + OpenZeppelin deps
├── hardhat.config.js    # Ganache (1337) + Sepolia (11155111) networks
├── src/                 # Solidity sources (Week 2-3)
├── test/                # Hardhat/chai tests (Week 2-3)
└── scripts/
    └── deploy.js        # Deploys contracts, exports ABIs to backend/contracts/abi/
```

## Prerequisites

- Node.js 20+ and npm (verified available).
- `npm install` inside `contracts/` (run in Week 2 when contracts are added).

## Networks

- **ganache** — local dev chain; reuses `GANACHE_URL` env (default `http://127.0.0.1:8545`), chainId 1337.
- **sepolia** — public testnet (Week 4); uses `SEPOLIA_RPC_URL` + `SEPOLIA_PRIVATE_KEY`
  env vars (same variables the backend already uses — one source of truth). Never commit keys.

## Hash convention (must match backend/frontend)

On-chain SIH hashes use **keccak256 → bytes32** per the Canonical Derivation & Encoding
section in `.kiro/specs/sih-26125-identity-asset-extension/data_model.md`. The existing
healthcare SHA-256 anchoring in `BlockchainService` is a separate, unchanged subsystem.

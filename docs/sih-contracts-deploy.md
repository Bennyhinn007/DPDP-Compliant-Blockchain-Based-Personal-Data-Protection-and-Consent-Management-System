# SIH 26125 Smart-Contract Deployment (Ganache & Sepolia)

Deploys the three additive SIH contracts — `PlatformAccessControl`,
`IdentityRegistry`, `AssetNFT` — and wires the backend to them. This is fully
independent of the DPDP healthcare platform, which keeps working with or without
a deployed chain (endpoints degrade gracefully / fail-closed on writes).

## Prerequisites

- Node.js 20+ and the contracts deps installed: `cd contracts && npm install`
- For Sepolia: a free RPC URL (Infura/Alchemy) and a **throwaway funded** testnet
  wallet (get test ETH from a Sepolia faucet).

## 1. Local Ganache (development)

1. Start Ganache (GUI or `ganache` CLI) on `http://127.0.0.1:8545` (chainId 1337).
2. Deploy:
   ```bash
   cd contracts
   npx hardhat run scripts/deploy.js --network ganache
   ```
3. The script prints the deployed addresses and writes ABIs to
   `backend/contracts/abi/`. Copy the three addresses into `backend/.env`:
   ```
   SIH_ACCESS_CONTROL_ADDRESS=0x...
   SIH_IDENTITY_REGISTRY_ADDRESS=0x...
   SIH_ASSET_NFT_ADDRESS=0x...
   BLOCKCHAIN_NETWORK=ganache
   ```
4. Restart the backend. `GET /api/v1/roles/matrix` should now report
   `chain_available: true`.

## 2. Sepolia (public testnet)

1. `cd contracts && cp .env.example .env`, then fill in:
   ```
   SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/YOUR_PROJECT_ID
   SEPOLIA_PRIVATE_KEY=0xyour_funded_testnet_private_key
   ```
   (`contracts/.env` is gitignored — never commit it.)
2. Deploy:
   ```bash
   npx hardhat run scripts/deploy.js --network sepolia
   ```
   Deployment takes ~30–90s per contract on the public testnet.
3. Copy the printed addresses into `backend/.env` and set:
   ```
   BLOCKCHAIN_NETWORK=sepolia
   SEPOLIA_RPC_URL=...
   SEPOLIA_PRIVATE_KEY=0x...   # backend admin key used to sign SIH txns
   SIH_ACCESS_CONTROL_ADDRESS=0x...
   SIH_IDENTITY_REGISTRY_ADDRESS=0x...
   SIH_ASSET_NFT_ADDRESS=0x...
   ```
4. Restart the backend. On-chain SIH operations now produce **real, publicly
   verifiable** Sepolia transactions (view them at `https://sepolia.etherscan.io`).

## Runtime address source (important)

The backend reads contract addresses ONLY from the environment/config
(`SIH_*_ADDRESS`). The `backend/contracts/abi/addresses.json` file emitted by the
deploy script is a convenience artifact, is **gitignored**, and is **not** used at
runtime. This keeps addresses environment-specific and prevents a stale/ephemeral
address from leaking into production.

## Verify

- `GET /api/v1/roles/matrix` → `chain_available: true`
- Create a DID (Identity Center) → on-chain `IdentityRegistered` event
- Grant a SIH role (Access Control Center) → `SIHRoleGranted` event
- Register an asset + mint NFT (Digital Asset Center) → `AssetMinted` event
- Events appear under the Blockchain Explorer "Smart-Contract Events" panel and in
  the dual audit trail (`chain_events` + hash-chained `audit_logs`).

## Safety notes

- Only hashes/DIDs/roles/tokenIds go on-chain — **never PHI**. Asset metadata is
  Fernet-encrypted off-chain; only its keccak256 hash is anchored.
- If the chain is unreachable: SIH **reads** return HTTP 200 with
  `chain_available:false`; SIH **critical writes** (mint/assign/transfer, role
  grant/revoke, DID revoke) **fail closed** with HTTP 503. Healthcare functionality
  is unaffected either way.

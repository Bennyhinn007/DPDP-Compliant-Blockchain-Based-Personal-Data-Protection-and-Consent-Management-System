# Demo Script (15 Minutes)

## Pre-Demo Setup

```bash
# Start MongoDB
mongod

# Start Ganache (optional but recommended for blockchain features)
npx ganache --deterministic --chain.chainId 1337

# Seed demo data
cd backend && python seeds/seed_demo.py

# Start backend
python run.py

# Start frontend (new terminal)
cd frontend && npm run dev
```

Open: http://localhost:5173

---

## Demo Flow

### 1. System Overview (1 min)

- Show the login page (professional healthcare portal design)
- Mention: DPDP Act compliance, blockchain anchoring, consent management
- Show API docs: http://localhost:5000/api/docs/

### 2. Patient Registration & Login (2 min)

- Click "Register" link
- Register new patient OR login with: `rajesh.kumar@gmail.com` / `Patient@123`
- Show the patient dashboard with:
  - Privacy Score
  - Active Consents (4)
  - Blockchain Anchors (10)
  - Healthcare Records (4)
  - Recent Activity timeline
  - Consent distribution chart

### 3. Personal Data Center (2 min)

- Navigate to "My Data Center"
- Show encrypted profile data (decrypted for display)
- Show "Download Data" (JSON export)
- Show healthcare records list
- Demonstrate "Correct" button → correction dialog
- Demonstrate "Erase" button → erasure dialog
- Point out: version tracking, blockchain references

### 4. Consent Management (2 min)

- Navigate to "Consent Center"
- Show 6 consent types with status badges
- Grant a new consent (e.g., Analytics Access)
  - Show blockchain transaction created
- Withdraw a consent
  - Show immediate access revocation

### 5. Integrity Verification (2 min)

- Navigate to "Integrity Verification"
- Show blockchain network status (Ganache connected)
- Click "Verify All Records"
- Show green "VERIFIED" badges
- Explain: current hash vs blockchain hash comparison

### 6. Chameleon Hash Center (3 min) ← KEY RESEARCH PAGE

- Navigate to "Chameleon Hash"
- Show side-by-side comparison:
  - Traditional Hash: modification breaks chain
  - Chameleon Hash: authorized modification preserves chain
- Show the mathematical formula: CH(m,r) = g^m · y^r mod p
- Walk through DPDP Right to Correction workflow (8 steps)
- Walk through DPDP Right to Erasure workflow (8 steps)
- Show proof history table (if corrections/erasures exist)
- Explain research contribution panel

### 7. Doctor Consent-Gated Access (2 min)

- Login as doctor (register one via API if needed)
- Search for "Rajesh"
- Show consent status indicator (green = consent active)
- Access patient records → show "Access Granted" with consent verification
- Try accessing patient without consent → show "Access Denied" with DPDP explanation
- Mention: both attempts are audit-logged

### 8. DPO/Admin Dashboard (1 min)

- Login as admin: `admin@dpdp-health.in` / `Admin@Secure123`
- Show Compliance & Governance Center:
  - Compliance Score gauge
  - System metrics (patients, records, anchors)
  - Rights requests (corrections/erasures count)
  - System integrity status
- Navigate to Compliance Breakdown:
  - Radar chart (5 categories)
  - Progress bars per category
  - Risk indicators

---

## Key Talking Points

- "Data never leaves Indian jurisdiction — DPDP Act Section 16-17"
- "Every action is audited with a blockchain-anchored hash chain"
- "Patients have full visibility into who accessed their data"
- "Chameleon hashing solves the conflict between blockchain immutability and DPDP erasure rights"
- "The system scored 97/100 on DPDP compliance scorecard"

## Viva Questions Preparation

| Question | Answer Location |
|----------|----------------|
| How does encryption work? | Personal Data Center → MongoDB stores ciphertext |
| How is blockchain used? | Integrity Verification → hash comparison |
| What if data needs to be deleted? | Chameleon Hash Center → erasure workflow |
| How is consent enforced? | Doctor Dashboard → Access Denied without consent |
| How do you audit? | Audit Timeline → hash-chained events |
| What is your research contribution? | Chameleon Hash Center → comparison + formula |

---

# SIH 26125 Extension Demo — Blockchain Identity, Access & Digital Assets (ADD-ON)

This is an ADDITIVE second workflow on top of the healthcare platform above. The
healthcare demo works with or without the chain; this section shows the SIH
identity/access/NFT layer. Nothing here changes existing healthcare behavior.

> Governing rule: ADD, DON'T REPLACE. No PHI goes on-chain. Healthcare records
> are never NFTs. Only hashes, DIDs, roles, and token IDs are anchored.

## Extra Setup (SIH contracts)

```bash
# 1. Deploy the three SIH contracts to local Ganache
cd contracts
npm install
npx hardhat run scripts/deploy.js --network ganache
# copy the printed addresses into backend/.env:
#   SIH_ACCESS_CONTROL_ADDRESS / SIH_IDENTITY_REGISTRY_ADDRESS / SIH_ASSET_NFT_ADDRESS

# 2. Restart the backend so it picks up the addresses.
```

Verify the chain wired up: `GET /api/v1/roles/matrix` → `chain_available: true`.
(If you skip this, all SIH reads still return 200 with `chain_available:false`,
and SIH critical writes fail closed with 503 — healthcare is unaffected either way.)

## SIH Demo Flow (~8 min)

### A. Decentralized Identity (DID) (2 min)

- Log in normally, open **Identity Center**.
- Click "Create My DID" — a secp256k1 keypair is generated client-side (private
  key stays in the browser; prototype custody). The DID
  `did:rakshaid:<id>` is registered off-chain and, if the chain is up, anchored
  on `IdentityRegistry` (`IdentityRegistered` event).
- Show DID login: challenge → EIP-191 signature → same JWT as password login.
- Talking point: "This is an ADDITIONAL cryptographic identity. It never
  replaces the existing user_id / password / OAuth / MFA login."
- Honesty label: rakshaid is a project-specific PROTOTYPE DID method, not an
  interoperable production DID network (ION/Sovrin).

### B. On-Chain Access Control (RBAC) (2 min)

- Log in as admin, open **Access Control Center**.
- Grant a SIH role (e.g. ASSET_MANAGER) to a DID → `PlatformAccessControl`
  `SIHRoleGranted` event. Show dual enforcement: application RBAC AND the
  on-chain role authority must agree.
- Talking point: "PlatformAccessControl is the single on-chain role authority.
  Existing healthcare roles (patient/doctor/pharmacy/dpo/admin) are untouched."

### C. Digital Asset as NFT (2 min)

- Open **Digital Asset Center**.
- Register a digital/organizational asset (e.g. a medical-device certificate):
  metadata is Fernet-encrypted off-chain; only its keccak256 hash is stored.
- Show the **no-PHI guard**: try adding a field like `diagnosis` or
  `patient_id` to asset metadata → rejected (422). Records are never NFTs.
- Mint the NFT (admin) → `AssetNFT` `AssetMinted` event. Assign / controlled
  transfer between DIDs. Verify ownership: on-chain owner-DID-hash +
  metadata-hash match the off-chain record.

### D. Optional RFID Physical-Presence Gate (1 min)

- Explain the optional `SIH_RFID_GATE_ENABLED` flag (OFF by default so it never
  blocks normal use). When ON, high-risk SIH ops (NFT mint, DID revoke) require
  a recent RFID tap; otherwise they return 403 `requires_physical_verification`.
- Talking point: "Reuses the existing physical-presence layer — no change to
  healthcare workflows, and the gate is off unless an operator opts in."

### E. Blockchain Explorer & Dual Audit (1 min)

- Open **Blockchain Explorer** → "Smart-Contract Events" panel: DID / role /
  asset events with tx hashes.
- Every SIH contract event is dual-recorded: `chain_events` AND the existing
  hash-chained `audit_logs`. Existing SHA-256 healthcare anchoring is a separate,
  unchanged subsystem (SIH uses keccak256).

## Optional: Sepolia Public Testnet (real, verifiable)

To show real public transactions instead of local Ganache, follow
`docs/sih-contracts-deploy.md`:

```bash
cd contracts && cp .env.example .env    # fill SEPOLIA_RPC_URL + SEPOLIA_PRIVATE_KEY
npx hardhat run scripts/deploy.js --network sepolia
# set BLOCKCHAIN_NETWORK=sepolia + the three SIH_*_ADDRESS in backend/.env, restart
```

SIH events are then viewable on `https://sepolia.etherscan.io`.

## SIH Talking Points

- "Additive extension — the healthcare product still runs standalone; the SIH
  layer degrades gracefully (reads) / fails closed (critical writes) when the
  chain is down."
- "No PHI ever touches the chain. Assets carry only a keccak256 metadata hash;
  the plaintext stays Fernet-encrypted in MongoDB."
- "One on-chain role authority (PlatformAccessControl); identity is
  registration-only (IdentityRegistry); assets are ERC-721 (AssetNFT)."
- "DID method is labeled a prototype; private keys are client-side only."

## SIH Viva Questions

| Question | Answer Location |
|----------|----------------|
| How is a DID created & authenticated? | Identity Center → keypair + EIP-191 challenge/response |
| Where is on-chain RBAC enforced? | Access Control Center → PlatformAccessControl (dual-enforced) |
| Why are records never NFTs? | Digital Asset Center → no-PHI guard (422 on PHI keys) |
| What goes on-chain for an asset? | Only keccak256 metadata hash + owner-DID-hash + tokenId |
| What happens if the chain is down? | Reads 200 (`chain_available:false`); critical writes 503 (fail-closed) |
| How is the extension isolated from healthcare? | ADD, DON'T REPLACE — new blueprints/services/collections, existing suite green |

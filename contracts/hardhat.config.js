/**
 * Hardhat configuration for the SIH 26125 identity/access/asset contracts.
 *
 * ADDITIVE to the existing DPDP healthcare platform — this is a self-contained
 * Solidity project under `contracts/`. It does NOT touch any existing backend,
 * frontend, database, or healthcare code.
 *
 * Networks:
 *   - ganache: local development chain (default, matches the existing
 *     BlockchainService GANACHE_URL / chainId 1337 convention).
 *   - sepolia: public testnet (Week 4). RPC + key come from env vars, never
 *     hard-coded. Reuses the same SEPOLIA_* vars already defined in the
 *     backend config so there is one source of truth.
 *
 * Solidity ^0.8.24 + OpenZeppelin Contracts v5 (installed in Week 2).
 */

require("@nomicfoundation/hardhat-toolbox");

// Minimal, dependency-free loader for contracts/.env (so `--network sepolia`
// picks up SEPOLIA_* without adding a dotenv dependency). Real environment
// variables always take precedence; the .env file only fills in gaps.
const fs = require("fs");
const path = require("path");
(function loadEnv() {
  const envPath = path.join(__dirname, ".env");
  if (!fs.existsSync(envPath)) return;
  for (const line of fs.readFileSync(envPath, "utf-8").split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq === -1) continue;
    const key = trimmed.slice(0, eq).trim();
    const val = trimmed.slice(eq + 1).trim();
    if (!(key in process.env)) process.env[key] = val;
  }
})();

const GANACHE_URL = process.env.GANACHE_URL || "http://127.0.0.1:8545";
const SEPOLIA_RPC_URL = process.env.SEPOLIA_RPC_URL || "";
const SEPOLIA_PRIVATE_KEY = process.env.SEPOLIA_PRIVATE_KEY || "";

/** @type {import('hardhat/config').HardhatUserConfig} */
module.exports = {
  solidity: {
    version: "0.8.24",
    settings: {
      optimizer: { enabled: true, runs: 200 },
      // OpenZeppelin Contracts v5 uses the `mcopy` opcode (Cancun). Solidity
      // 0.8.24 supports targeting the Cancun EVM.
      evmVersion: "cancun",
    },
  },
  paths: {
    sources: "./src",
    tests: "./test",
    artifacts: "./artifacts",
    cache: "./cache",
  },
  networks: {
    ganache: {
      url: GANACHE_URL,
      chainId: 1337,
    },
    sepolia: {
      url: SEPOLIA_RPC_URL,
      chainId: 11155111,
      accounts: SEPOLIA_PRIVATE_KEY ? [SEPOLIA_PRIVATE_KEY] : [],
    },
  },
};

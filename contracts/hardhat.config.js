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

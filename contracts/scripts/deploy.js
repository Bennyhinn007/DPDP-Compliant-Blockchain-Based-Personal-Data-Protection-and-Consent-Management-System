/**
 * Deploy PlatformAccessControl + IdentityRegistry (Phase 2), then export ABIs
 * and deployed addresses to backend/contracts/abi/ for the Python ContractService.
 *
 * AssetNFT is deployed in Week 3 (Phase 3) — intentionally NOT here.
 *
 * Usage:
 *   npx hardhat run scripts/deploy.js --network ganache
 *   npx hardhat run scripts/deploy.js --network sepolia   (Week 4)
 */

const fs = require("fs");
const path = require("path");
const { ethers, artifacts, network } = require("hardhat");

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log(`[deploy] network=${network.name} deployer=${deployer.address}`);

  // 1. PlatformAccessControl (single role authority) — admin = deployer.
  const PAC = await ethers.getContractFactory("PlatformAccessControl");
  const pac = await PAC.deploy(deployer.address);
  await pac.waitForDeployment();
  const pacAddress = await pac.getAddress();
  console.log(`[deploy] PlatformAccessControl -> ${pacAddress}`);

  // 2. IdentityRegistry (identity only; reads ADMIN gate from PAC).
  const REG = await ethers.getContractFactory("IdentityRegistry");
  const registry = await REG.deploy(pacAddress);
  await registry.waitForDeployment();
  const regAddress = await registry.getAddress();
  console.log(`[deploy] IdentityRegistry -> ${regAddress}`);

  // 3. AssetNFT (ERC-721 digital assets; role-gated via PAC) — Phase 3.
  const NFT = await ethers.getContractFactory("AssetNFT");
  const nft = await NFT.deploy(pacAddress);
  await nft.waitForDeployment();
  const nftAddress = await nft.getAddress();
  console.log(`[deploy] AssetNFT -> ${nftAddress}`);

  // 4. Export ABIs + addresses to backend/contracts/abi/.
  const outDir = path.resolve(__dirname, "..", "..", "backend", "contracts", "abi");
  fs.mkdirSync(outDir, { recursive: true });

  const exportAbi = (name) => {
    const art = artifacts.readArtifactSync(name);
    fs.writeFileSync(
      path.join(outDir, `${name}.json`),
      JSON.stringify({ abi: art.abi }, null, 2)
    );
  };
  exportAbi("PlatformAccessControl");
  exportAbi("IdentityRegistry");
  exportAbi("AssetNFT");

  const addresses = {
    network: network.name,
    chainId: Number((await ethers.provider.getNetwork()).chainId),
    PlatformAccessControl: pacAddress,
    IdentityRegistry: regAddress,
    AssetNFT: nftAddress,
    deployer: deployer.address,
    deployedAt: new Date().toISOString(),
  };
  fs.writeFileSync(
    path.join(outDir, "addresses.json"),
    JSON.stringify(addresses, null, 2)
  );

  console.log(`[deploy] ABIs + addresses written to ${outDir}`);
  console.log(`[deploy] Set these env vars for the backend:`);
  console.log(`  SIH_ACCESS_CONTROL_ADDRESS=${pacAddress}`);
  console.log(`  SIH_IDENTITY_REGISTRY_ADDRESS=${regAddress}`);
  console.log(`  SIH_ASSET_NFT_ADDRESS=${nftAddress}`);
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});

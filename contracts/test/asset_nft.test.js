const { expect } = require("chai");
const { ethers } = require("hardhat");

/**
 * Phase 3 contract tests: AssetNFT (ERC-721) with role-gated mint/assign/transfer,
 * revocation, and events. Roles are enforced via PlatformAccessControl.
 */

const OWNER_DID = ethers.keccak256(ethers.toUtf8Bytes("did:rakshaid:owner"));
const NEW_DID = ethers.keccak256(ethers.toUtf8Bytes("did:rakshaid:newowner"));
const META = ethers.keccak256(ethers.toUtf8Bytes('{"name":"Radar Module","type":"device"}'));
const ASSET_TYPE = 1;

describe("AssetNFT", function () {
  let pac, nft, admin, manager, outsider;

  beforeEach(async function () {
    [admin, manager, outsider] = await ethers.getSigners();
    const PAC = await ethers.getContractFactory("PlatformAccessControl");
    pac = await PAC.deploy(admin.address);
    await pac.waitForDeployment();

    const NFT = await ethers.getContractFactory("AssetNFT");
    nft = await NFT.deploy(await pac.getAddress());
    await nft.waitForDeployment();

    // Give `manager` the on-chain MANAGER_ROLE (address-keyed OZ role).
    await pac.connect(admin).grantRole(await pac.MANAGER_ROLE(), manager.address);
  });

  it("admin can mint and emits AssetMinted; ownership/metadata recorded", async function () {
    await expect(nft.connect(admin).mint(OWNER_DID, META, ASSET_TYPE))
      .to.emit(nft, "AssetMinted")
      .withArgs(1, OWNER_DID, META, ASSET_TYPE);
    expect(await nft.ownerDidOf(1)).to.equal(OWNER_DID);
    expect(await nft.metadataHashOf(1)).to.equal(META);
    expect(await nft.assetTypeOf(1)).to.equal(ASSET_TYPE);
    expect(await nft.statusOf(1)).to.equal(1); // Active
    expect(await nft.totalMinted()).to.equal(1);
  });

  it("non-admin cannot mint (reverts)", async function () {
    await expect(nft.connect(outsider).mint(OWNER_DID, META, ASSET_TYPE))
      .to.be.revertedWith("caller is not ADMIN");
    // Even a MANAGER cannot mint.
    await expect(nft.connect(manager).mint(OWNER_DID, META, ASSET_TYPE))
      .to.be.revertedWith("caller is not ADMIN");
  });

  it("admin or manager can assign to a new DID; emits AssetAssigned", async function () {
    await nft.connect(admin).mint(OWNER_DID, META, ASSET_TYPE);
    await expect(nft.connect(manager).assign(1, NEW_DID))
      .to.emit(nft, "AssetAssigned")
      .withArgs(1, NEW_DID, manager.address);
    expect(await nft.ownerDidOf(1)).to.equal(NEW_DID);
  });

  it("outsider cannot assign (reverts)", async function () {
    await nft.connect(admin).mint(OWNER_DID, META, ASSET_TYPE);
    await expect(nft.connect(outsider).assign(1, NEW_DID))
      .to.be.revertedWith("caller is not ADMIN/MANAGER");
  });

  it("admin/manager controlledTransfer updates owner and emits event", async function () {
    await nft.connect(admin).mint(OWNER_DID, META, ASSET_TYPE);
    await expect(nft.connect(admin).controlledTransfer(1, NEW_DID))
      .to.emit(nft, "AssetTransferred")
      .withArgs(1, OWNER_DID, NEW_DID);
    expect(await nft.ownerDidOf(1)).to.equal(NEW_DID);
  });

  it("unauthorized controlledTransfer reverts", async function () {
    await nft.connect(admin).mint(OWNER_DID, META, ASSET_TYPE);
    await expect(nft.connect(outsider).controlledTransfer(1, NEW_DID))
      .to.be.revertedWith("caller not authorized to transfer");
  });

  it("admin can revoke (setStatus) and blocks further assign/transfer", async function () {
    await nft.connect(admin).mint(OWNER_DID, META, ASSET_TYPE);
    await expect(nft.connect(admin).setStatus(1, 2)) // Revoked
      .to.emit(nft, "AssetStatusChanged")
      .withArgs(1, 2);
    expect(await nft.statusOf(1)).to.equal(2);
    await expect(nft.connect(admin).assign(1, NEW_DID)).to.be.revertedWith("asset not active");
    await expect(nft.connect(admin).controlledTransfer(1, NEW_DID)).to.be.revertedWith("asset not active");
  });

  it("token ids increment", async function () {
    await nft.connect(admin).mint(OWNER_DID, META, ASSET_TYPE);
    await nft.connect(admin).mint(NEW_DID, META, 2);
    expect(await nft.ownerDidOf(2)).to.equal(NEW_DID);
    expect(await nft.totalMinted()).to.equal(2);
  });
});

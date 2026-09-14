const { expect } = require("chai");
const { ethers } = require("hardhat");

/**
 * Phase 2 contract tests: PlatformAccessControl (single role authority) +
 * IdentityRegistry (identity only). Covers role gating, register/revoke/verify,
 * events, and the single-authority relationship. AssetNFT is Week 3.
 */

const DID_HASH = ethers.keccak256(ethers.toUtf8Bytes("did:rakshaid:alice"));
const PUB_KEY_HASH = ethers.keccak256(ethers.toUtf8Bytes("alice-pubkey"));

describe("PlatformAccessControl", function () {
  let pac, admin, manager, outsider;

  beforeEach(async function () {
    [admin, manager, outsider] = await ethers.getSigners();
    const PAC = await ethers.getContractFactory("PlatformAccessControl");
    pac = await PAC.deploy(admin.address);
    await pac.waitForDeployment();
  });

  it("assigns ADMIN_ROLE and DEFAULT_ADMIN_ROLE to the deployer admin", async function () {
    expect(await pac.hasRole(await pac.ADMIN_ROLE(), admin.address)).to.equal(true);
    expect(await pac.hasRole(await pac.DEFAULT_ADMIN_ROLE(), admin.address)).to.equal(true);
  });

  it("admin can grant a SIH role to a DID and emits event", async function () {
    const MANAGER_ROLE = await pac.MANAGER_ROLE();
    await expect(pac.connect(admin).grantSIHRole(DID_HASH, MANAGER_ROLE))
      .to.emit(pac, "SIHRoleGranted")
      .withArgs(DID_HASH, MANAGER_ROLE, admin.address);
    expect(await pac.didHasRole(DID_HASH, MANAGER_ROLE)).to.equal(true);
  });

  it("non-admin cannot grant a SIH role (reverts)", async function () {
    const MANAGER_ROLE = await pac.MANAGER_ROLE();
    await expect(
      pac.connect(outsider).grantSIHRole(DID_HASH, MANAGER_ROLE)
    ).to.be.reverted;
  });

  it("admin can revoke a SIH role and emits event", async function () {
    const USER_ROLE = await pac.USER_ROLE();
    await pac.connect(admin).grantSIHRole(DID_HASH, USER_ROLE);
    await expect(pac.connect(admin).revokeSIHRole(DID_HASH, USER_ROLE))
      .to.emit(pac, "SIHRoleRevoked")
      .withArgs(DID_HASH, USER_ROLE, admin.address);
    expect(await pac.didHasRole(DID_HASH, USER_ROLE)).to.equal(false);
  });

  it("rejects unknown roles", async function () {
    const bogus = ethers.keccak256(ethers.toUtf8Bytes("BOGUS_ROLE"));
    await expect(pac.connect(admin).grantSIHRole(DID_HASH, bogus)).to.be.revertedWith("unknown role");
  });
});

describe("IdentityRegistry", function () {
  let pac, registry, admin, outsider;

  beforeEach(async function () {
    [admin, outsider] = await ethers.getSigners();
    const PAC = await ethers.getContractFactory("PlatformAccessControl");
    pac = await PAC.deploy(admin.address);
    await pac.waitForDeployment();

    const REG = await ethers.getContractFactory("IdentityRegistry");
    registry = await REG.deploy(await pac.getAddress());
    await registry.waitForDeployment();
  });

  it("admin can register a DID and emits event", async function () {
    await expect(registry.connect(admin).register(DID_HASH, PUB_KEY_HASH))
      .to.emit(registry, "IdentityRegistered")
      .withArgs(DID_HASH, PUB_KEY_HASH);
    expect(await registry.isVerified(DID_HASH)).to.equal(true);
    expect(await registry.pubKeyHashOf(DID_HASH)).to.equal(PUB_KEY_HASH);
    expect(await registry.statusOf(DID_HASH)).to.equal(1);
  });

  it("non-admin cannot register (single authority = PlatformAccessControl)", async function () {
    await expect(
      registry.connect(outsider).register(DID_HASH, PUB_KEY_HASH)
    ).to.be.revertedWith("caller is not ADMIN");
  });

  it("cannot register the same DID twice", async function () {
    await registry.connect(admin).register(DID_HASH, PUB_KEY_HASH);
    await expect(
      registry.connect(admin).register(DID_HASH, PUB_KEY_HASH)
    ).to.be.revertedWith("already registered");
  });

  it("admin can revoke; isVerified becomes false", async function () {
    await registry.connect(admin).register(DID_HASH, PUB_KEY_HASH);
    await expect(registry.connect(admin).revoke(DID_HASH))
      .to.emit(registry, "IdentityRevoked")
      .withArgs(DID_HASH);
    expect(await registry.isVerified(DID_HASH)).to.equal(false);
    expect(await registry.statusOf(DID_HASH)).to.equal(2);
  });

  it("cannot revoke a non-active DID", async function () {
    await expect(registry.connect(admin).revoke(DID_HASH)).to.be.revertedWith("not active");
  });

  it("unregistered DID is not verified", async function () {
    expect(await registry.isVerified(DID_HASH)).to.equal(false);
    expect(await registry.statusOf(DID_HASH)).to.equal(0);
  });

  it("newly granted admin (via PlatformAccessControl) can register", async function () {
    const ADMIN_ROLE = await pac.ADMIN_ROLE();
    await pac.connect(admin).grantRole(ADMIN_ROLE, outsider.address);
    await expect(registry.connect(outsider).register(DID_HASH, PUB_KEY_HASH))
      .to.emit(registry, "IdentityRegistered");
  });
});

/**
 * Deployment script (SKELETON — Week 1 scaffold).
 *
 * In Week 2-3 this will:
 *   1. Deploy PlatformAccessControl (single role authority)
 *   2. Deploy IdentityRegistry (identity only; reads roles from PlatformAccessControl)
 *   3. Deploy AssetNFT (ERC-721; Week 3)
 *   4. Wire DEFAULT_ADMIN_ROLE to the deployer / backend admin key
 *   5. Export ABIs + deployed addresses to backend/contracts/abi/
 *
 * No contracts exist yet, so this script intentionally does nothing but print a
 * notice. It is safe to run and will be filled in during Week 2.
 */

async function main() {
  console.log(
    "[deploy] SIH 26125 contracts are not authored yet (Week 1 scaffold). " +
      "Contract deployment is implemented in Week 2 (IdentityRegistry + " +
      "PlatformAccessControl) and Week 3 (AssetNFT)."
  );
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});

# SIH 26125 — Integration Strategy

> Make the SIH layer feel like part of ONE unified platform, without disturbing
> the primary DPDP healthcare system.

## Mechanisms

1. **Feature flag `SIH_FEATURES_ENABLED`** (default enabled in dev). Toggling it off
   fully disables the SIH layer at runtime → the platform reverts to the pure
   healthcare product. This is both an integration switch and a rollback lever.

2. **DID optional per user.** Absence of a DID never blocks any healthcare flow.
   Existing password/OAuth/MFA login remains the default path.

3. **JWT bridge.** DID challenge-response authentication issues the **same** JWT via
   the existing `AuthService`, so all downstream authorization, session handling, and
   audit continue to work unchanged.

4. **Flexible role mapping (config-driven, additive).** Healthcare roles keep their
   names (patient/doctor/pharmacy_staff/dpo/admin). SIH roles (ADMIN/MANAGER/AUDITOR/USER)
   are added separately. An optional advisory mapping (e.g., `admin` ↔ `ADMIN_ROLE`)
   supports the demo without renaming anything.

5. **Blockchain service extension.** A new `ContractService` composes with the existing
   `BlockchainService`. Existing `anchor_record` / `verify_record` behavior is untouched;
   contract calls are new methods.

6. **Dual-audit wiring.** A thin hook emits on-chain contract events and caches them to
   `chain_events`, in addition to the existing `AuditService.log_event`. Neither replaces
   the other.

7. **DID ↔ consent (R14, optional).** Nullable DID references on consents; the existing
   consent path remains the default and works without DIDs.

8. **Graceful degradation (by endpoint class).** If the chain is unreachable:
   read-only SIH endpoints return **HTTP 200** with `chain_available:false` and serve
   cached/off-chain data; critical blockchain write operations **fail closed** with
   **HTTP 503** and `chain_available:false` (no partial state). Healthcare functionality
   is fully operational and independent of chain availability.

## Unified-platform UX

One navigation, one login, one design system. The user moves between Healthcare,
Privacy, Security, Identity, Digital Assets, Blockchain, and Administration as
sections of the same product — not two apps.

# SIH 26125 — Rollback & Regression Strategy

## Regression gate (every phase)

Run the existing test suite (**verified baseline: 164 passed, 1 skipped**) plus the
phase's new tests. Merge only if all previously-passing tests still pass. Manual
healthcare smoke checklist each phase:

- [ ] Healthcare login (password / OAuth / MFA)
- [ ] Create healthcare record + encryption round-trip
- [ ] Consent grant → doctor access allowed
- [ ] Consent withdraw → doctor access denied
- [ ] Audit hash-chain integrity intact
- [ ] Blockchain anchor + integrity verification
- [ ] Redaction / chameleon workflow
- [ ] RFID physical-presence (where applicable)

## Rollback levers (fastest → most thorough)

1. **Runtime flag:** set `SIH_FEATURES_ENABLED=false` → the entire SIH layer is
   disabled instantly; the platform reverts to pure healthcare behavior. No code revert.
2. **Branch revert:** each phase lives on its own branch; because changes are
   backward-compatible and largely new-file additions, `git revert` of a phase branch
   removes SIH additions cleanly without touching healthcare logic.
3. **DB safety:** new collections only; new fields on existing collections are
   nullable/defaulted, so dropping them is non-destructive and existing documents
   remain valid.
4. **Chain safety:** contract addresses via env; missing/unreachable chain degrades
   gracefully; healthcare never depends on chain availability.

## Non-negotiables

- No history rewrite; no force-push.
- No phase merges if any existing core workflow breaks.
- Existing files are only minimally modified where technically necessary for
  integration, with existing behavior preserved and the regression suite green.

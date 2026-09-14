"""
Dual-Audit Hook — SIH 26125 Phase 3 (ADDITIVE).

Records a blockchain/contract action in BOTH audit layers, per the spec:
  1. The existing off-chain hash-chained `audit_logs` (via AuditService) — unchanged.
  2. A cache of the on-chain event in `chain_events` (for the explorer + on-chain
     audit view).

Neither replaces the other. This helper is best-effort: audit failures never
block the primary operation.
"""

from app.utils.helpers import generate_uuid, utc_now


def record_chain_event(db, *, event_name: str, contract: str, tx_hash: str = None,
                       args: dict = None, actor_id: str = None, actor_role: str = None,
                       reason: str = None, source_ip: str = None) -> None:
    """Write to chain_events + the existing hash-chained audit_logs (best-effort)."""
    # 1. on-chain event cache (explorer + on-chain audit layer)
    try:
        db["chain_events"].insert_one({
            "_id": generate_uuid(),
            "event_name": event_name,
            "contract": contract,
            "tx_hash": tx_hash,
            "block_number": None,  # populated by an indexer in a later pass if desired
            "args": args or {},
            "actor_id": actor_id,
            "indexed_at": utc_now(),
        })
    except Exception:
        pass

    # 2. existing off-chain hash-chained audit trail (unchanged subsystem)
    try:
        from app.services.audit_service import AuditService
        AuditService(db).log_event(
            actor_id=actor_id or "system",
            actor_role=actor_role or "admin",
            action_type="update",
            resource_type="blockchain",
            resource_id=tx_hash or event_name,
            reason=reason or f"On-chain event: {event_name}",
            details={"event": event_name, "contract": contract, "tx_hash": tx_hash, "args": args or {}},
            source_ip=source_ip,
        )
    except Exception:
        pass

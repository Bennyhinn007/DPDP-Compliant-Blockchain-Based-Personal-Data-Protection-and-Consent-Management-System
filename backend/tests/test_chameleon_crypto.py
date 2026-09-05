"""
Tests for the REAL cryptographic Chameleon Hash primitive.

These tests prove the genuine discrete-log chameleon hash works:
  - Deterministic hashing
  - Correct verification
  - Trapdoor collision: different content, IDENTICAL hash (the key property)
  - Collision resistance without the trapdoor
"""

from app.services.chameleon_crypto import ChameleonHash


def test_key_generation():
    """Keys are generated with y = g^x mod p."""
    ch = ChameleonHash()
    keys = ch.generate_keys()
    assert keys.y == pow(keys.g, keys.x, keys.p)
    assert 1 <= keys.x < keys.q


def test_hash_is_deterministic_for_same_r():
    """Same message + same r => same hash."""
    ch = ChameleonHash()
    keys = ch.generate_keys()
    h1, r = ch.hash(keys, "patient diagnosis: hypertension")
    h2, _ = ch.hash(keys, "patient diagnosis: hypertension", r)
    assert h1 == h2


def test_verify_accepts_valid():
    """verify() returns True for a correctly computed hash."""
    ch = ChameleonHash()
    keys = ch.generate_keys()
    h, r = ch.hash(keys, "original record")
    assert ch.verify(keys, "original record", r, h) is True


def test_verify_rejects_wrong_message_without_collision():
    """A different message with the SAME r must NOT match (no trapdoor used)."""
    ch = ChameleonHash()
    keys = ch.generate_keys()
    h, r = ch.hash(keys, "original record")
    assert ch.verify(keys, "tampered record", r, h) is False


def test_trapdoor_collision_produces_identical_hash():
    """
    THE KEY PROPERTY:
    Using the trapdoor, a NEW message produces the SAME hash as the original.
    This is what makes authorized redaction possible on a blockchain.
    """
    ch = ChameleonHash()
    keys = ch.generate_keys()

    original = "Diagnosis code: I25.1"
    corrected = "Diagnosis code: I25.10 (corrected under DPDP Section 12)"

    h_original, r_original = ch.hash(keys, original)

    # Trapdoor holder finds the collision
    r_new = ch.find_collision(keys, original, r_original, corrected)

    h_corrected, _ = ch.hash(keys, corrected, r_new)

    # Different content, SAME hash — the blockchain anchor stays valid.
    assert h_original == h_corrected
    assert original != corrected
    assert r_original != r_new


def test_collision_verifies():
    """The collision r' passes verification against the original hash."""
    ch = ChameleonHash()
    keys = ch.generate_keys()

    original = "record v1"
    new = "record v2 redacted"
    h, r = ch.hash(keys, original)
    r_new = ch.find_collision(keys, original, r, new)

    assert ch.verify(keys, new, r_new, h) is True


def test_multiple_sequential_redactions():
    """A record can be redacted multiple times, hash stays constant each time."""
    ch = ChameleonHash()
    keys = ch.generate_keys()

    v1 = "version 1"
    h, r = ch.hash(keys, v1)

    v2 = "version 2"
    r = ch.find_collision(keys, v1, r, v2)
    assert ch.verify(keys, v2, r, h)

    v3 = "version 3 [REDACTED]"
    r = ch.find_collision(keys, v2, r, v3)
    assert ch.verify(keys, v3, r, h)

"""
Chameleon Hash — REAL Cryptographic Implementation.

This is a genuine discrete-logarithm based Chameleon Hash, NOT a simulation.

A Chameleon Hash is a trapdoor collision-resistant hash function:
    CH(m, r) = (g^m * y^r) mod p

Properties:
  1. Collision resistance WITHOUT the trapdoor:
     Without the secret key x, it is computationally infeasible to find
     (m', r') != (m, r) such that CH(m, r) == CH(m', r').
  2. Trapdoor collision WITH the secret key:
     The holder of the trapdoor x can, for ANY new message m', compute r'
     such that CH(m, r) == CH(m', r'). This is the "authorized redaction"
     capability — the record content changes, but the hash stays identical,
     so the blockchain anchor remains valid.

Mathematical foundation:
    Public parameters:
        p  — large safe prime (p = 2q + 1, q prime)
        q  — prime order of the subgroup
        g  — generator of the order-q subgroup of Z_p*
    Key pair:
        x  — trapdoor / secret key, random in [1, q-1]
        y  — public key, y = g^x mod p
    Hash:
        CH(m, r) = (g^m * y^r) mod p,  where m, r are reduced mod q
    Collision (trapdoor holder only):
        Given (m, r) and a new m', find r' such that:
            g^m * y^r  ==  g^m' * y^r'   (mod p)
        Since y = g^x:
            m + x*r  ==  m' + x*r'   (mod q)
            r'  =  (m - m' + x*r) * x^{-1}   (mod q)

This module provides the primitive. The healthcare workflow (authorization,
versioning, audit, blockchain anchoring) sits on top of it.
"""

import hashlib
import secrets
from dataclasses import dataclass


# ─────────────────────────────────────────────────────────────────────────
# PUBLIC PARAMETERS
# A verified safe prime p = 2q + 1 where BOTH p and q are prime.
# Using RFC 3526 Group 5 (1536-bit MODP). This is a real, standardized,
# cryptographically-strong group. Because q = (p-1)/2 is prime, every
# x in [1, q-1] is invertible mod q — required for trapdoor collisions.
# ─────────────────────────────────────────────────────────────────────────

# RFC 3526 1536-bit MODP Group (Group 5). p is a safe prime.
_P = int(
    "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
    "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
    "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
    "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
    "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D"
    "C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F"
    "83655D23DCA3AD961C62F356208552BB9ED529077096966D"
    "670C354E4ABC9804F1746C08CA237327FFFFFFFFFFFFFFFF",
    16,
)
_Q = (_P - 1) // 2          # prime order of the subgroup (q is prime for RFC 3526 safe primes)
# In a safe-prime group, 2 generates the full group of order 2q. Squaring it
# (g = 2^2 = 4) yields a generator of the prime-order-q subgroup, so that all
# exponent arithmetic works cleanly modulo the prime q.
_G = 4


@dataclass
class ChameleonKeyPair:
    """A chameleon hash key pair."""
    p: int          # prime modulus (public)
    q: int          # subgroup order (public)
    g: int          # generator (public)
    y: int          # public key  y = g^x mod p
    x: int          # trapdoor / secret key (KEEP SECRET)


def _hash_to_int(message: str, q: int) -> int:
    """Deterministically map an arbitrary string message to an integer mod q."""
    digest = hashlib.sha256(message.encode("utf-8")).digest()
    return int.from_bytes(digest, "big") % q


class ChameleonHash:
    """
    Real discrete-log Chameleon Hash primitive.

    Usage:
        ch = ChameleonHash()
        keys = ch.generate_keys()
        h, r = ch.hash(keys, "original record content")
        # later, the trapdoor holder redacts:
        r2 = ch.find_collision(keys, "original record content", r, "corrected content")
        assert ch.verify(keys, "corrected content", r2, h)   # True — hash unchanged!
    """

    def __init__(self, p: int = _P, q: int = _Q, g: int = _G):
        self.p = p
        self.q = q
        self.g = g

    # ── Key generation ────────────────────────────────────────────────
    def generate_keys(self) -> ChameleonKeyPair:
        """Generate a chameleon key pair. x is the trapdoor, y is public."""
        x = secrets.randbelow(self.q - 2) + 1          # x in [1, q-1]
        y = pow(self.g, x, self.p)                     # y = g^x mod p
        return ChameleonKeyPair(p=self.p, q=self.q, g=self.g, y=y, x=x)

    # ── Hashing ───────────────────────────────────────────────────────
    def hash(self, keys: ChameleonKeyPair, message: str, r: int | None = None):
        """
        Compute CH(m, r) = (g^m * y^r) mod p.

        Args:
            keys: key pair (public part used)
            message: the message string to hash
            r: randomness; if None, a fresh random r is generated

        Returns:
            (hash_value:int, r:int)
        """
        if r is None:
            r = secrets.randbelow(self.q - 2) + 1
        m = _hash_to_int(message, self.q)
        gm = pow(self.g, m, self.p)
        yr = pow(keys.y, r, self.p)
        h = (gm * yr) % self.p
        return h, r

    # ── Verification ──────────────────────────────────────────────────
    def verify(self, keys: ChameleonKeyPair, message: str, r: int, expected_hash: int) -> bool:
        """Return True if CH(message, r) == expected_hash."""
        h, _ = self.hash(keys, message, r)
        return h == expected_hash

    # ── Trapdoor collision (authorized redaction) ─────────────────────
    def find_collision(
        self,
        keys: ChameleonKeyPair,
        original_message: str,
        original_r: int,
        new_message: str,
    ) -> int:
        """
        Using the trapdoor x, find r' such that:
            CH(original_message, original_r) == CH(new_message, r')

        Derivation:
            g^m  * y^r   ==  g^m' * y^r'      (mod p)
            m + x*r      ==  m' + x*r'        (mod q)     [since y = g^x]
            r'  =  (m - m' + x*r) * x^{-1}    (mod q)

        Only possible with the secret trapdoor x. This is the mathematical
        heart of a redactable blockchain — the content changes, the hash does not.
        """
        m = _hash_to_int(original_message, self.q)
        m_new = _hash_to_int(new_message, self.q)
        x = keys.x
        x_inv = pow(x, -1, self.q)                       # modular inverse of x mod q
        r_new = ((m - m_new + x * original_r) * x_inv) % self.q
        return r_new

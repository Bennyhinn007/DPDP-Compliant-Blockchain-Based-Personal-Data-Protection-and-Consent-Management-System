/**
 * Browser Identity Wallet — SIH 26125 (ADDITIVE, prototype-grade).
 *
 * secp256k1 keypair generation + EIP-191 `personal_sign` signing, entirely in
 * the browser. The PRIVATE KEY never leaves the client — only the public key and
 * signatures are sent to the backend. Derivation MUST match the backend
 * `did_service.py` and the Canonical Derivation & Encoding spec.
 *
 * PROTOTYPE custody: the key is kept in localStorage for the demo. This is NOT
 * production-grade key management (a hardware wallet / secure enclave would be
 * used in production) — labeled as such in the UI.
 */

import * as secp from "@noble/secp256k1";
import { keccak_256 } from "@noble/hashes/sha3";
import { utf8ToBytes, bytesToHex, hexToBytes } from "@noble/hashes/utils";

const STORAGE_KEY = "sih_did_wallet_v1";

export interface Wallet {
  privateKey: string; // 0x-hex (client-only)
  publicKey: string; // 0x04|| X || Y  (65-byte uncompressed, 0x-hex)
  address: string; // 0x-hex Ethereum address
}

function hex0x(b: Uint8Array): string {
  return "0x" + bytesToHex(b);
}

/** Ethereum address = last 20 bytes of keccak256(pubkey without 0x04 prefix). */
function addressFromUncompressed(pub65: Uint8Array): string {
  const hash = keccak_256(pub65.slice(1)); // drop 0x04 prefix
  return "0x" + bytesToHex(hash.slice(-20));
}

/** Generate a fresh secp256k1 wallet (uncompressed pubkey, matches backend). */
export function generateWallet(): Wallet {
  const priv = secp.utils.randomPrivateKey();
  const pub = secp.getPublicKey(priv, false); // 65-byte uncompressed
  return {
    privateKey: hex0x(priv),
    publicKey: hex0x(pub),
    address: addressFromUncompressed(pub),
  };
}

/** Persist the wallet in localStorage (prototype custody). */
export function saveWallet(w: Wallet): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(w));
}

export function loadWallet(): Wallet | null {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Wallet;
  } catch {
    return null;
  }
}

export function clearWallet(): void {
  localStorage.removeItem(STORAGE_KEY);
}

/**
 * EIP-191 `personal_sign` over a UTF-8 message.
 *
 * Builds the digest exactly as Ethereum does:
 *   keccak256( "\x19Ethereum Signed Message:\n" + len(message) + message )
 * then signs recoverably and returns a 65-byte `r || s || v` signature as 0x-hex,
 * where v ∈ {27, 28}. This is what `eth_account.recover_message` expects.
 */
export async function personalSign(message: string, privateKeyHex: string): Promise<string> {
  const msgBytes = utf8ToBytes(message);
  const prefix = utf8ToBytes(`\x19Ethereum Signed Message:\n${msgBytes.length}`);
  const digest = keccak_256(concatBytes(prefix, msgBytes));

  const priv = hexToBytes(privateKeyHex.startsWith("0x") ? privateKeyHex.slice(2) : privateKeyHex);
  const sig = await secp.signAsync(digest, priv);
  // noble v2 returns a Signature with recovery bit; build r||s||v (v = 27 + recovery).
  const compact = sig.toCompactRawBytes(); // 64 bytes r||s
  const v = 27 + (sig.recovery ?? 0);
  const full = new Uint8Array(65);
  full.set(compact, 0);
  full[64] = v;
  return hex0x(full);
}

function concatBytes(a: Uint8Array, b: Uint8Array): Uint8Array {
  const out = new Uint8Array(a.length + b.length);
  out.set(a, 0);
  out.set(b, a.length);
  return out;
}

/**
 * Utility functions for the application.
 */

import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge Tailwind classes with conflict resolution.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format an ISO timestamp into a readable date-time string.
 */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

/**
 * Format an ISO timestamp into a readable date string.
 */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

/**
 * Truncate a hash for display (e.g., 0xabc...def).
 */
export function truncateHash(hash: string | null | undefined, chars = 6): string {
  if (!hash) return "—";
  if (hash.length <= chars * 2 + 2) return hash;
  return `${hash.slice(0, chars + 2)}...${hash.slice(-chars)}`;
}

/**
 * Capitalize and humanize a snake_case string.
 */
export function humanize(value: string | null | undefined): string {
  if (!value) return "—";
  return value
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/**
 * Healthcare provider / organization display name.
 * Overridable via VITE_PROVIDER_ORG_NAME; default matches the backend
 * PROVIDER_ORG_NAME so the Provider Portal header and record provenance agree.
 */
export const PROVIDER_ORG_NAME: string =
  (import.meta.env.VITE_PROVIDER_ORG_NAME as string | undefined) || "CityCare Hospital";

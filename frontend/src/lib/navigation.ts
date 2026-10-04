/**
 * Role-Based Navigation Configuration.
 */

import {
  LayoutDashboard,
  Database,
  ShieldCheck,
  Clock,
  FileCheck,
  BarChart3,
  PieChart,
  Users,
  Stethoscope,
  Fingerprint,
  Link2,
  Settings,
  Nfc,
  KeyRound,
  Boxes,
  LockKeyhole,
  UserPlus,
  type LucideIcon,
} from "lucide-react";
import type { UserRole } from "@/types";

export interface NavItem {
  label: string;
  path: string;
  icon: LucideIcon;
  roles: UserRole[];
}

export const NAV_ITEMS: NavItem[] = [
  {
    label: "Dashboard",
    path: "/dashboard",
    icon: LayoutDashboard,
    roles: ["patient"],
  },
  {
    label: "My Data Center",
    path: "/my-data",
    icon: Database,
    roles: ["patient"],
  },
  {
    label: "Consent Center",
    path: "/consents",
    icon: ShieldCheck,
    roles: ["patient"],
  },
  {
    label: "Audit Timeline",
    path: "/timeline",
    icon: Clock,
    roles: ["patient"],
  },
  {
    label: "Integrity Verification",
    path: "/verify",
    icon: FileCheck,
    roles: ["patient"],
  },
  {
    label: "Chameleon Hash",
    path: "/chameleon-hash",
    icon: Fingerprint,
    roles: ["patient"],
  },
  {
    label: "Provider Portal",
    path: "/doctor",
    icon: Stethoscope,
    roles: ["doctor"],
  },
  {
    label: "Compliance Dashboard",
    path: "/dpo",
    icon: BarChart3,
    roles: ["admin", "dpo"],
  },
  {
    label: "Compliance Breakdown",
    path: "/dpo/compliance",
    icon: PieChart,
    roles: ["admin", "dpo"],
  },
  {
    label: "Register User",
    path: "/admin/register-patient",
    icon: UserPlus,
    roles: ["admin"],
  },
  {
    // Registration staff portal — their ONLY nav item (own restricted path).
    label: "Register User",
    path: "/staff/register-patient",
    icon: UserPlus,
    roles: ["registration_staff"],
  },
  {
    label: "User Management",
    path: "/admin/users",
    icon: Users,
    roles: ["admin"],
  },
  {
    label: "DPDP Operations",
    path: "/admin/operations",
    icon: Settings,
    roles: ["admin"],
  },
  {
    label: "Blockchain Explorer",
    path: "/admin/blockchain",
    icon: Link2,
    roles: ["admin"],
  },
  {
    label: "Physical Access Log",
    path: "/admin/physical-access",
    icon: Nfc,
    roles: ["admin"],
  },
  // ── SIH 26125 Identity Extension (ADDITIVE) ──
  {
    label: "Identity Center",
    path: "/identity",
    icon: KeyRound,
    roles: ["patient", "doctor", "pharmacy_staff", "admin", "dpo"],
  },
  {
    label: "Digital Assets",
    path: "/assets",
    icon: Boxes,
    roles: ["patient", "doctor", "pharmacy_staff", "admin", "dpo"],
  },
  {
    label: "Access Control",
    path: "/admin/access-control",
    icon: LockKeyhole,
    roles: ["admin", "dpo"],
  },
];

export function getNavItemsForRole(role: UserRole): NavItem[] {
  return NAV_ITEMS.filter((item) => item.roles.includes(role));
}

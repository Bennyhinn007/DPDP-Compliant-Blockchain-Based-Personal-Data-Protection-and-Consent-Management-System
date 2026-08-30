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
    label: "Doctor Dashboard",
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
];

export function getNavItemsForRole(role: UserRole): NavItem[] {
  return NAV_ITEMS.filter((item) => item.roles.includes(role));
}

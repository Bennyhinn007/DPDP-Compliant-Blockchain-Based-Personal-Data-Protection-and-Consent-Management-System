/**
 * Sidebar Navigation.
 *
 * Role-based navigation menu with gradient active-state highlighting,
 * animated active indicator, and icon hover motion.
 */

import { NavLink } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuth } from "@/contexts/AuthContext";
import { getNavItemsForRole } from "@/lib/navigation";
import { Logo } from "@/components/shared/Logo";
import { cn } from "@/lib/utils";

export function Sidebar() {
  const { user } = useAuth();
  if (!user) return null;

  const navItems = getNavItemsForRole(user.role);

  return (
    <aside className="hidden w-64 flex-shrink-0 flex-col border-r border-neutral-200 bg-white lg:flex">
      {/* Logo */}
      <div className="flex h-16 items-center border-b border-neutral-200 px-6">
        <Logo size={38} withWordmark subtitle="Secure Platform" />
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-4">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              cn(
                "group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
                isActive
                  ? "bg-primary-600 text-white shadow-sm"
                  : "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900"
              )
            }
          >
            {({ isActive }) => (
              <>
                {/* Animated left indicator */}
                {isActive && (
                  <motion.span
                    layoutId="sidebar-active-indicator"
                    className="absolute -left-1 top-1/2 h-6 w-1 -translate-y-1/2 rounded-full bg-white"
                    transition={{ type: "spring", stiffness: 400, damping: 30 }}
                  />
                )}
                <item.icon
                  className={cn(
                    "h-5 w-5 transition-transform duration-200 group-hover:scale-105",
                    isActive ? "text-white" : "text-neutral-400 group-hover:text-neutral-700"
                  )}
                />
                {item.label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-neutral-200 p-4">
        <div className="rounded-lg bg-success/10 px-3 py-2.5 text-xs text-success ring-1 ring-success/20">
          <div className="flex items-center gap-1.5 font-medium">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
            </span>
            DPDP Compliant
          </div>
          <div className="mt-0.5 text-success/70">Data residency: India</div>
        </div>
      </div>
    </aside>
  );
}
